"""Gemma-facing prompt assets — deliberately separate from game profiles.

Ownership rule — hot vs cold configuration:
- profiles/<game>.yaml  configures the HARNESS (buttons, ladder, ratchet,
  escalation, drivers). COLD: loaded once at startup; changing it means
  tearing the harness down and starting a new run segment. Each run keeps a
  snapshot of the profile it ran under, so results stay attributable.
- prompts/<game>/       configures GEMMA. HOT by construction: prompt.md is
  read fresh from disk on EVERY LLM invocation, so checkpoint edits are live
  on the next decision with no reload machinery.

Layout:
    prompts/<game>/prompt.md    THE prompt: rules, controls, tips, and the
                                placeholders {behaviors} {goals} {ram} {recent}
                                the harness fills per call. Keep the dynamic
                                placeholders at the bottom so the static head
                                stays prefix-cacheable.
    prompts/<game>/goals.md     seed copied to runs/<game>/<run-id>/goals.md
                                when a new run starts (legacy strategy feed)
    prompts/<game>/quests.yaml  seed copied to runs/<game>/<run-id>/
                                quests.yaml when a new run starts — the
                                structured quest tree (checkpoint-authored,
                                harness-fed piecemeal; supersedes goals.md
                                when present)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class GamePrompts:
    prompt_path: Path | None = None
    initial_goals: str | None = None
    initial_quests: str | None = None

    @classmethod
    def load(cls, base: Path, game: str) -> "GamePrompts":
        d = base / "prompts" / game
        prompt = d / "prompt.md"
        goals = d / "goals.md"
        quests = d / "quests.yaml"
        return cls(
            prompt_path=prompt if prompt.is_file() else None,
            initial_goals=goals.read_text(encoding="utf-8") if goals.is_file() else None,
            initial_quests=quests.read_text(encoding="utf-8")
            if quests.is_file() else None,
        )
