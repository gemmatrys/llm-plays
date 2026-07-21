"""CLI entry point.

    python -m harness --profile profiles/pokemon_red.yaml --policy fish
    python -m harness --profile profiles/pokemon_red.yaml --policy llm \
        --endpoint http://arcbox:8000 --model google/gemma-3-27b-it
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from . import drivers
from .behaviors import BehaviorLibrary
from .executor import Executor
from .loop import GameLoop
from .policy import FishPolicy, LLMPolicy
from .profile import GameProfile
from .prompts import GamePrompts
from .runlog import RunLog
from .stream import StreamState, start_server
from .sync import HotSync
from .watchdog import Watchdog


def main() -> None:
    ap = argparse.ArgumentParser(prog="harness")
    ap.add_argument("--profile", required=True, help="path to a game profile YAML")
    ap.add_argument("--policy", choices=["fish", "llm", "none"], default="fish",
                    help="'none' = pure watchdog fallback (ladder test)")
    ap.add_argument("--endpoint", default="http://127.0.0.1:8000",
                    help="OpenAI-compatible inference endpoint (llm policy)")
    ap.add_argument("--model", default="gemma",
                    help="served model name (serve_gemma.sh registers 'gemma')")
    ap.add_argument("--reasoning", choices=["none", "low", "medium", "high"],
                    default="low",
                    help="Gemma 4 thinking effort; server must run "
                         "--reasoning-parser gemma4 for any value except none "
                         "(and with the parser on, keep this on: vllm#39130)")
    ap.add_argument("--iterations", type=int, default=None,
                    help="stop after N decisions (default: run forever)")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--stream-port", type=int, default=8700,
                    help="port for the OBS overlay / state.json (0 = off); note "
                         "Windows reserves 8563-8662 for Hyper-V on some machines")
    ap.add_argument("--publish", action="store_true",
                    help="live-stream goals/memory to the git remote: an async "
                         "watcher types changes into live/ a chunk per commit")
    args = ap.parse_args()

    base = Path.cwd()
    profile = GameProfile.load(args.profile)  # harness config: runtime-immutable
    prompts = GamePrompts.load(base, profile.name)  # Gemma-facing: checkpoint-synced
    library = BehaviorLibrary(profile.buttons, profile.skills_dirs, base)

    runlog = RunLog(base, profile.name, args.run_id,
                    initial_goals=prompts.initial_goals,
                    alert_cmd=profile.escalation.alert_cmd,
                    alert_cooldown_s=profile.escalation.alert_cooldown_s)
    # segment marker: a restart (hotfix, recovery) must not smear its downtime
    # into decision-rate metrics — the briefing sums ACTIVE hours between these
    runlog.log_metric("harness_start", resumed=runlog.resumed)

    if args.policy == "fish":
        policy = FishPolicy(profile.buttons)
    elif args.policy == "llm":
        def _prompt_alarm(problem: str) -> None:
            # a bad checkpoint edit must self-report, not silently degrade
            runlog.log_metric("prompt_invalid", detail=problem)
            runlog.escalate("prompt_invalid",
                            f"prompt.md rejected ({problem}); playing on last good version")

        policy = LLMPolicy(args.endpoint, args.model, library,
                           prompt_path=prompts.prompt_path,
                           timeout_s=profile.ladder.llm_timeout_s,
                           max_plan=profile.ladder.max_plan_len,
                           on_prompt_invalid=_prompt_alarm,
                           reasoning=args.reasoning)
    else:
        policy = None

    eyes, hands, extras = drivers.create(profile)
    executor = Executor(hands, extras, profile.ratchet.savestate_slot)
    watchdog = Watchdog(policy, library, profile.ladder,
                        on_llm_failure=lambda why: runlog.log_metric(
                            "llm_failure", detail=str(why)[:300]))
    # bind the run to its harness config: a profile edit = teardown + new run,
    # and this snapshot keeps every run's numbers attributable to one config
    shutil.copyfile(args.profile, runlog.dir / "profile.yaml")

    # seeding report — the prompt must exist before the game starts
    if runlog.resumed:
        print("[harness] resumed run: existing goals.md kept")
    elif prompts.initial_goals:
        print(f"[harness] goals.md seeded from prompts/{profile.name}/goals.md")
    else:
        print(f"[harness] WARNING: no prompts/{profile.name}/goals.md — "
              f"run starts with generic default goals")
    if args.policy == "llm":
        if prompts.prompt_path:
            print(f"[harness] prompt: {prompts.prompt_path} (read fresh every call)")
        else:
            print(f"[harness] WARNING: no prompts/{profile.name}/prompt.md — "
                  f"using the built-in fallback template")

    stream = None
    if args.stream_port:
        # the overlay header shows the player's name, not harness internals
        stream = StreamState(game=profile.name,
                             policy=args.model if args.policy == "llm" else args.policy)
        start_server(stream, args.stream_port)
        if args.policy == "llm":
            policy.on_stream = stream.stream_thinking  # live-stream reasoning
        print(f"[harness] overlay: http://127.0.0.1:{args.stream_port}/ "
              f"(add as OBS Browser Source)")

    sync = HotSync(base, profile.skills_dirs, library)

    publisher = None
    if args.publish:
        from .publish import LivePublisher
        publisher = LivePublisher(base, runlog)
        publisher.start()
        print("[harness] live-publishing goals/memory to the 'live' branch "
              "on the git remote (main stays code-only)")

    print(f"[harness] game={profile.name} driver={profile.driver} "
          f"policy={args.policy} run={runlog.dir}")
    try:
        GameLoop(profile, eyes, executor, extras, watchdog, runlog, base,
                 stream=stream, sync=sync).run(args.iterations)
    finally:
        if publisher is not None:
            publisher.stop()


if __name__ == "__main__":
    main()
