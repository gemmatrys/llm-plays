"""Local LLM policy — a deliberately dumb prompt renderer.

The harness owns NO prompt text. Each decision:
1. read prompts/<game>/prompt.md fresh from disk (edits are live immediately),
2. validate it (required placeholders, size cap) — an invalid file falls back
   to the last good version and raises an escalation instead of sending garbage,
3. substitute the placeholders {behaviors} {goals} {ram} {recent} {max_plan},
4. send the rendered text + the current frame to the OpenAI-compatible endpoint,
5. enforce the plan JSON schema at the decoder (maxItems = the profile's
   max_plan_len — the same number rendered into {max_plan}, one owner per fact).

Everything the model is told — rules, controls, tips — lives in the prompt file
where checkpoints (or a human) can rewrite it without touching harness code.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
from pathlib import Path

import requests

from .. import items

from ..behaviors import BehaviorLibrary
from ..types import Behavior, Observation

REQUIRED_PLACEHOLDERS = ("{behaviors}", "{goals}")
MAX_TEMPLATE_CHARS = 8000  # ~2k tokens; a prompt this long is a latency bug

# Fallback only — a real game should ship prompts/<game>/prompt.md.
DEFAULT_TEMPLATE = """You control a video game character. Reply with a plan of \
1-{max_plan} behaviors from the allowed list, plus one short sentence of \
reasoning. Keep plans short when the screen is new or risky; if the screen \
changes unexpectedly your remaining plan is cancelled automatically. If your \
recent actions repeat without progress, do something different.

Use the optional "memory" field to rewrite your own notes (below) whenever your \
location or task changes: where you are, what you are doing, what comes next.

## Allowed behaviors
{behaviors}

## Your notes
{memory}

## Goals
{goals}

## Known game state
{ram}

## Map around you
{tilemap}

## Recent actions (oldest first)
{recent}"""


def _collapse_counted(behaviors: list[str]) -> list[str]:
    """Display the 36 counted walk variants as one legend entry — the schema
    enum still carries every exact name; this only tidies the listing."""
    counted = re.compile(r"walk_(north|south|west|east)_[1-9]$")
    out = [n for n in behaviors if not counted.fullmatch(n)]
    if len(out) != len(behaviors):
        out.append("walk_north_<1-9> / walk_south_<1-9> / walk_west_<1-9> / "
                   "walk_east_<1-9> (walk EXACTLY that many tiles - e.g. a "
                   "'3 south, 4 east' bearing = walk_south_3, walk_east_4)")
    return out


def _state_line(key: str, value, spec) -> str | None:
    """One state field -> the sentence the model reads. spec comes from the
    profile's state_lines: a {v} template, a value->sentence map (enums), or
    None to hide the field. Unknown values / absent specs fall back to the
    raw line rather than dropping information."""
    if spec is None:
        return None
    if isinstance(spec, dict):
        line = spec.get(value, spec.get(str(value)))
        return line if line is not None else f"- {key}: {value}"
    if isinstance(spec, str):
        return spec.replace("{v}", str(value))
    return f"- {key}: {value}"


def render_prompt(template: str, behaviors: list[str], goals: str,
                  ram: dict | None, recent: list[str], max_plan: int = 8,
                  memory: str = "", tilemap: str = "",
                  state_lines: dict | None = None) -> str:
    """Plain string substitution — no logic, no formatting surprises."""
    if ram and state_lines:
        rendered = (_state_line(k, v, state_lines[k]) if k in state_lines
                    else f"- {k}: {v}" for k, v in ram.items())
        ram_text = "\n".join(s for s in rendered if s is not None)
    elif ram:
        ram_text = "\n".join(f"- {k}: {v}" for k, v in ram.items())
    else:
        ram_text = "(unknown)"
    recent_text = ", ".join(recent[-15:]) if recent else "(none)"
    return (template
            .replace("{behaviors}", ", ".join(_collapse_counted(behaviors)))
            .replace("{goals}", goals.strip())
            .replace("{ram}", ram_text)
            .replace("{recent}", recent_text)
            .replace("{memory}", memory.strip() or "(empty - write some!)")
            .replace("{tilemap}", tilemap.strip() or "(no map available)")
            .replace("{max_plan}", str(max_plan)))


# Gemma4's chain-of-thought (<|channel>thought\n ... <channel|>) is unrecoverable
# from a NON-streaming reply on this llm-scaler build — the detokenizer strips
# the delimiters from both `content` and `reasoning_content` regardless of
# skip_special_tokens (vllm#38855). Streaming sidesteps this entirely: the server
# emits clean incremental `delta.reasoning` chunks, which is why LLMPolicy always
# streams when reasoning is on (see decide()).
MAX_THINKING_CHARS = 2000  # keep the logged/streamed record bounded


class LLMPolicy:
    name = "llm"

    def __init__(self, endpoint: str, model: str, library: BehaviorLibrary,
                 prompt_path: str | Path | None = None,
                 timeout_s: float = 30.0, max_image_px: int = 480,
                 max_plan: int = 8, on_prompt_invalid=None,
                 reasoning: str = "none", state_lines: dict | None = None):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.library = library
        self.prompt_path = Path(prompt_path) if prompt_path else None
        self.timeout_s = timeout_s
        self.max_image_px = max_image_px
        self.max_plan = max_plan
        self.on_prompt_invalid = on_prompt_invalid  # called once per bad version
        # optional callback(text, done) to stream the thinking transcript into the
        # overlay live as tokens arrive (set by cli when an overlay is running)
        self.on_stream = None
        # Gemma 4 thinking: "none" disables; "low"/"medium"/"high" require the
        # server to run with --reasoning-parser gemma4 (which strips the
        # thinking tokens before the JSON schema is applied). Caveat: with the
        # parser enabled, requests WITHOUT thinking silently lose structured
        # output (vllm#39130) — so keep reasoning on when the server has it on.
        self.reasoning = reasoning
        self.state_lines = state_lines or {}
        self.last_reason = ""  # the model's "why" — logged and shown on stream
        self.last_thinking = ""  # thinking transcript (logprobs-recovered), logged
        self.last_memory = None  # notes rewrite from the last decision, if any
        self.last_done_goal = None  # numbered goal the model reports finished
        self.last_prompt_hash = ""  # logged per decision for attribution
        self._last_good = DEFAULT_TEMPLATE
        self._last_bad: str | None = None
        self._enum_names: list[str] = library.names()

    def _template(self) -> str:
        """Read the prompt file; on an invalid edit keep playing on the last
        good version and alarm (once per distinct bad content) instead of
        silently sending garbage until the next checkpoint."""
        if self.prompt_path is None or not self.prompt_path.is_file():
            return self._last_good
        raw = self.prompt_path.read_text(encoding="utf-8")
        missing = [p for p in REQUIRED_PLACEHOLDERS if p not in raw]
        if missing or len(raw) > MAX_TEMPLATE_CHARS:
            if raw != self._last_bad:
                self._last_bad = raw
                problem = (f"missing placeholders: {', '.join(missing)}" if missing
                           else f"template too long: {len(raw)} > {MAX_TEMPLATE_CHARS} chars")
                if self.on_prompt_invalid is not None:
                    self.on_prompt_invalid(problem)
            return self._last_good
        self._last_good = raw
        self._last_bad = None
        return raw

    def decide(self, obs: Observation) -> list[Behavior]:
        self.last_memory = None  # reset: only a fresh "memory" field counts
        self.last_done_goal = None
        template = self._template()
        self.last_prompt_hash = hashlib.sha256(template.encode()).hexdigest()[:12]
        # per-decision dynamic intents (item use/buy): full names go into the
        # grammar enum; the DISPLAYED list gets the collapsed legend lines
        dyn_names = obs.extra.get("dynamic_behaviors", [])
        dyn_legend = obs.extra.get("dynamic_legend", [])
        shown = self.library.names() + dyn_legend
        self._enum_names = self.library.names() + dyn_names
        text = render_prompt(template, shown,
                             obs.goals, obs.ram, obs.recent, self.max_plan,
                             memory=obs.memory, tilemap=obs.tilemap,
                             state_lines=self.state_lines)
        # forced notes refresh: the loop flags stale notes (map change / age);
        # "memory" becomes schema-REQUIRED so the decoder cannot omit it
        stale_notes = obs.extra.get("stale_notes")
        if stale_notes:
            text += ("\n\nIMPORTANT: your notes are STALE - " + stale_notes +
                     ". This reply MUST include a \"memory\" field rewriting "
                     "them: where you are NOW, what you are doing, what is "
                     "next. Do not repeat the old notes.")
        # rung-1 confusion intervention (loop/slow-streak detectors): the
        # harness saw a failing trajectory the model cannot see from inside
        # one decision - hand it the trajectory, demand a change of approach
        intervention = obs.extra.get("intervention")
        if intervention:
            text += "\n\nIMPORTANT: " + intervention
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url",
                     "image_url": {"url": self._frame_data_url(obs)}},
                ]},
            ],
            # thinking budget: when confused the model thinks LONGEST, and if
            # thinking eats all of max_tokens the answer never comes (content
            # is None) — exactly when a decision matters most. Sized to the
            # relaxed 240s enforce window: 4000 tokens is ~160-200s at the 31B's
            # ~20-25 tok/s, inside the HTTP deadline, so hard cases get real
            # room while typical decisions stop early (model emits <channel|>
            # then the short JSON). Truncation still degrades safely via the
            # ladder (content None -> llm_failed -> fallback).
            "max_tokens": 6000 if self.reasoning != "none" else 200,
            "temperature": 0.7,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "plan",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "plan": {
                                "type": "array",
                                "items": {"type": "string",
                                          "enum": self._enum_names},
                                "minItems": 1,
                                "maxItems": self.max_plan,
                            },
                            # kept short on purpose: at ~25 tok/s every extra
                            # 25 tokens of eloquence costs a second of latency
                            "why": {"type": "string", "maxLength": 100},
                            # the model's own notes; omitted = unchanged, so it
                            # only costs decode tokens when something changed
                            "memory": {"type": "string", "maxLength": 400},
                            # "goal N is finished" — the harness stamps [DONE]
                            # on that numbered goal so it stops being re-chased
                            "done_goal": {"type": "integer",
                                          "minimum": 0, "maximum": 50},
                        },
                        "required": (["plan", "memory"] if stale_notes
                                     else ["plan"]),
                        "additionalProperties": False,
                    },
                },
            },
        }
        if self.reasoning != "none":
            # reasoning_effort is ignored by the current llm-scaler build;
            # enable_thinking works (and coexists with the JSON schema).
            payload["chat_template_kwargs"] = {"enable_thinking": True}
        # STREAM the generation: the overlay shows the model reasoning live as
        # delta.reasoning chunks arrive, and only once the stream finishes do we
        # parse the plan and act — so the reasoning appears BEFORE the button
        # press, not after. In streaming mode the server emits clean incremental
        # `reasoning` deltas directly (unlike the non-streaming reply, where the
        # channel delimiters get stripped before we ever see them — vllm#38855),
        # so no logprobs reconstruction is needed here. HTTP read deadline sits
        # BELOW the watchdog's so a slow call frees the worker before it gives up.
        payload["stream"] = True
        reasoning_parts, content_parts, pushed = [], [], 0
        if self.on_stream is not None:
            self.on_stream("", False)  # clear the panel for a fresh generation
        try:
            r = requests.post(f"{self.endpoint}/v1/chat/completions", json=payload,
                              stream=True, timeout=max(10.0, self.timeout_s - 10.0))
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0].get("delta") or {}
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                if delta.get("content"):
                    content_parts.append(delta["content"])
                if delta.get("reasoning"):
                    reasoning_parts.append(delta["reasoning"])
                    if self.on_stream is not None and pushed < len(reasoning_parts):
                        # TAIL of the transcript: a head cap froze the overlay
                        # solid once thinking passed the limit (every push was
                        # the same truncated prefix) — precisely on the long
                        # decisions where watching the reasoning matters most
                        text = "".join(reasoning_parts)[-MAX_THINKING_CHARS:]
                        self.on_stream(text, False)
                        pushed = len(reasoning_parts)
        finally:
            # tail for the log too: the END of the reasoning (the conclusion
            # that produced the plan) is the part worth keeping when bounded
            self.last_thinking = "".join(reasoning_parts)[-MAX_THINKING_CHARS:]
            if self.on_stream is not None:
                self.on_stream(self.last_thinking, True)  # mark generation done
        content = "".join(content_parts).strip()
        if not content:
            raise ValueError("no answer content; thinking may have consumed the "
                             "max_tokens budget")
        try:
            action = json.loads(content)
        except json.JSONDecodeError:  # tolerate any leading text before the JSON
            i, j = content.find("{"), content.rfind("}")
            if i == -1 or j == -1:
                raise ValueError(f"no JSON object in content: {content[:80]!r}")
            action = json.loads(content[i:j + 1])
        plan = []
        for name in action["plan"]:
            behavior = self.library.get(name) or items.stub(name)
            if behavior is None and name.startswith("walk_to_") \
                    and name in self._enum_names:
                # landmark walk minted this decision; loop resolves it
                behavior = Behavior(name=name, source="builtin", steps=[])
            if behavior is None:
                raise ValueError(f"model chose unknown behavior {name!r}")
            plan.append(behavior)
        self.last_reason = action.get("why", "")
        self.last_memory = action.get("memory")  # None = keep previous notes
        self.last_done_goal = action.get("done_goal")
        return plan

    # The JUDGE (tripwire-judge step validation, PLAN): one tiny screenshot-only
    # query. Template is checkpoint-owned like everything model-facing —
    # prompts/<game>/verify.md (hot, published) with an {expect} placeholder;
    # this fallback only exists so a missing file degrades loud, not broken.
    DEFAULT_VERIFY_TEMPLATE = """You are checking ONE thing on this game \
screenshot. Expected: {expect}
Answer from the screenshot only, immediately - do not deliberate. \
"seen" = what the screen actually shows, one short sentence."""

    def verify(self, frame, expect: str) -> tuple[bool, str]:
        """Judge call: does the settled screen match `expect`? Returns
        (matches, seen). Raises on transport/parse failure - the executor
        fails open. Kept minimal: no goals, no ram, no history - the judge
        rules on the screenshot alone so its verdict can't be argued into
        agreement by stale context."""
        vp = (self.prompt_path.parent / "verify.md"
              if self.prompt_path is not None else None)
        template = (vp.read_text(encoding="utf-8")
                    if vp is not None and vp.is_file()
                    else self.DEFAULT_VERIFY_TEMPLATE)
        if "{expect}" not in template:
            template = self.DEFAULT_VERIFY_TEMPLATE
        img = frame.image
        if max(img.size) > self.max_image_px:
            scale = self.max_image_px / max(img.size)
            img = img.resize((int(img.width * scale), int(img.height * scale)),
                             resample=0)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": template.replace("{expect}", expect)},
                {"type": "image_url", "image_url": {"url": url}},
            ]}],
            # thinking stays ON when the server parser is on (vllm#39130:
            # without it, structured output silently breaks) - the budget is
            # sized so a binary look-and-answer finishes fast, and the
            # template orders an immediate answer
            "max_tokens": 1200 if self.reasoning != "none" else 120,
            "temperature": 0.0,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "verify", "schema": {
                    "type": "object",
                    "properties": {
                        "matches": {"type": "boolean"},
                        "seen": {"type": "string", "maxLength": 120},
                    },
                    "required": ["matches", "seen"],
                    "additionalProperties": False,
                }}},
        }
        if self.reasoning != "none":
            payload["chat_template_kwargs"] = {"enable_thinking": True}
        r = requests.post(f"{self.endpoint}/v1/chat/completions", json=payload,
                          timeout=min(60.0, self.timeout_s))
        r.raise_for_status()
        content = (r.json()["choices"][0]["message"].get("content") or "").strip()
        if not content:
            raise ValueError("judge reply empty (thinking ate the budget)")
        try:
            verdict = json.loads(content)
        except json.JSONDecodeError:
            i, j = content.find("{"), content.rfind("}")
            if i == -1 or j == -1:
                raise ValueError(f"judge reply not JSON: {content[:80]!r}")
            verdict = json.loads(content[i:j + 1])
        return bool(verdict.get("matches")), str(verdict.get("seen", ""))[:200]

    def _frame_data_url(self, obs: Observation) -> str:
        img = obs.frame.image
        if max(img.size) > self.max_image_px:
            scale = self.max_image_px / max(img.size)
            img = img.resize((int(img.width * scale), int(img.height * scale)),
                             resample=0)  # NEAREST keeps pixel art crisp
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
