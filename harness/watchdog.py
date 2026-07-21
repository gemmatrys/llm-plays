"""The fallback ladder — invariant I1.

Guarantees a Decision is always produced, and tracks which rung produced it.
Policy calls run under a timeout in a worker thread; a hung LLM call can never
stall the loop.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout

from . import items
from .behaviors import BehaviorLibrary, fish_move
from .interfaces import Policy
from .profile import LadderConfig
from .types import Behavior, Decision, Observation, Rung, Step


class Watchdog:
    def __init__(self, policy: Policy | None, library: BehaviorLibrary, cfg: LadderConfig,
                 on_llm_failure=None):
        self.policy = policy
        self.library = library
        self.cfg = cfg
        self.on_llm_failure = on_llm_failure  # called with a reason string
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="policy")
        self._consecutive_failures = 0
        self._successes_since_demotion = 0
        self._demoted = policy is None  # no policy (fish-only run) = permanently demoted
        fb = cfg.scripted_fallback
        self._fallback_cycle = [fb] if isinstance(fb, str) else list(fb)
        self._fallback_i = 0

    def decide(self, obs: Observation) -> Decision:
        if not self._demoted:
            decision = self._try_llm(obs)
            if decision is not None:
                return decision
        else:
            self._successes_since_demotion += 1
            if (self.policy is not None
                    and self._successes_since_demotion >= self.cfg.promote_after_successes):
                self._demoted = False
                self._consecutive_failures = 0
        return self._fallback()

    # -- rung 1 -------------------------------------------------------------
    def _try_llm(self, obs: Observation) -> Decision | None:
        fut = self._pool.submit(self.policy.decide, obs)
        try:
            result = fut.result(timeout=self.cfg.llm_timeout_s)
        except FutTimeout:
            fut.cancel()
            return self._llm_failed("timeout")
        except Exception as e:  # noqa: BLE001 — any policy error is a ladder event
            return self._llm_failed(f"error: {e}")

        # Trust condition: every step of the plan must exist in the library.
        plan = result if isinstance(result, list) else [result]
        plan = plan[: self.cfg.max_plan_len]
        if not plan:
            return self._llm_failed("empty plan")
        resolved = []
        for b in plan:
            known = self.library.get(b.name)
            if known is None and (items.is_item(b.name)
                                  or b.name.startswith("walk_to_")):
                # dynamic item intent (use_<item>/buy_<item>_x<n>): valid by
                # construction, resolved into real steps by the loop at
                # execution time when bag/shop context is known
                known = b
            if known is None:
                return self._llm_failed(f"unknown behavior {b.name!r}")
            resolved.append(known)
        self._consecutive_failures = 0
        reason = getattr(self.policy, "last_reason", "") or ""
        return Decision(behaviors=resolved, rung=Rung.LLM, reason=reason,
                        prompt_hash=getattr(self.policy, "last_prompt_hash", ""),
                        memory_update=getattr(self.policy, "last_memory", None),
                        done_goal=getattr(self.policy, "last_done_goal", None),
                        thinking=getattr(self.policy, "last_thinking", ""))

    def _llm_failed(self, why: str) -> None:
        self._consecutive_failures += 1
        if self.on_llm_failure is not None:
            self.on_llm_failure(why)  # a silent brain outage cost us a debug cycle once
        if self._consecutive_failures >= self.cfg.demote_after_failures:
            self._demoted = True
            self._successes_since_demotion = 0
        return None

    # -- rungs 2–4 ----------------------------------------------------------
    def _fallback(self) -> Decision:
        # cycle the configured list so sustained fallback stretches vary their
        # behavior (interact AND move) instead of repeating one wrong answer
        for _ in range(len(self._fallback_cycle)):
            name = self._fallback_cycle[self._fallback_i % len(self._fallback_cycle)]
            self._fallback_i += 1
            scripted = self.library.get(name)
            if scripted is not None:
                return Decision(behaviors=[scripted], rung=Rung.SCRIPTED,
                                reason=f"fallback:{name}")
        if self.cfg.allow_random:
            # rung 4: a randomized macro from the fish repertoire (wander /
            # mash-dialogue / mash-direction / mash-B / press-any) so a brain
            # outage still does structured random things, not one-tile twitching.
            move = fish_move(self.library.buttons)
            return Decision(behaviors=[move], rung=Rung.RANDOM,
                            reason=f"fish: {move.name}")
        idle = self.library.get(self.cfg.safe_idle) or Behavior(
            name="wait", steps=[Step(op="wait", wait_frames=60)])
        return Decision(behaviors=[idle], rung=Rung.SAFE_IDLE, reason="safe idle")
