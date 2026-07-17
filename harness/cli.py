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
    ap.add_argument("--model", default="google/gemma-3-27b-it")
    ap.add_argument("--iterations", type=int, default=None,
                    help="stop after N decisions (default: run forever)")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--stream-port", type=int, default=8600,
                    help="port for the OBS overlay / state.json (0 = off)")
    args = ap.parse_args()

    base = Path.cwd()
    profile = GameProfile.load(args.profile)  # harness config: runtime-immutable
    prompts = GamePrompts.load(base, profile.name)  # Gemma-facing: checkpoint-synced
    library = BehaviorLibrary(profile.buttons, profile.skills_dirs, base)

    runlog = RunLog(base, profile.name, args.run_id,
                    initial_goals=prompts.initial_goals)

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
                           on_prompt_invalid=_prompt_alarm)
    else:
        policy = None

    eyes, hands, extras = drivers.create(profile)
    executor = Executor(hands, extras, profile.ratchet.savestate_slot)
    watchdog = Watchdog(policy, library, profile.ladder)
    # bind the run to its harness config: a profile edit = teardown + new run,
    # and this snapshot keeps every run's numbers attributable to one config
    shutil.copyfile(args.profile, runlog.dir / "profile.yaml")

    # seeding report — the prompt must exist before the game starts
    if prompts.initial_goals:
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
        stream = StreamState(game=profile.name, policy=args.policy)
        start_server(stream, args.stream_port)
        print(f"[harness] overlay: http://127.0.0.1:{args.stream_port}/ "
              f"(add as OBS Browser Source)")

    sync = HotSync(base, profile.skills_dirs, library)

    print(f"[harness] game={profile.name} driver={profile.driver} "
          f"policy={args.policy} run={runlog.dir}")
    GameLoop(profile, eyes, executor, extras, watchdog, runlog, base,
             stream=stream, sync=sync).run(args.iterations)


if __name__ == "__main__":
    main()
