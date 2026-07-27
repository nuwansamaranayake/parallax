"""Key-gated narration: the LLM polishes the deterministic brief; a deterministic gate
decides which sentences survive.

The LLM is a sensor, not a judge (DOCTRINE). It may reword; it may not introduce numbers or
cite stats that do not exist. Every generated sentence must name the stat ids it rests on.
The gate accepts a sentence only when (a) it cites at least one stat id, (b) every cited id
exists, and (c) every numeric token in the sentence matches a stored stat value. Rejected
sentences are kept and reported, never silently dropped.

This stage is strictly optional polish: the deterministic brief IS the product. Without an
OPENROUTER_API_KEY the API refuses loudly with a typed 503 (Standard 3, no silent fallback).
"""
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from .brief import Stat, fmt, verify_groundedness

NARRATION_SCHEMA = {
    "name": "brief_narration",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "stat_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["text", "stat_ids"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["sentences"],
        "additionalProperties": False,
    },
}


class CompletesJson(Protocol):
    def complete(self, *, model: str, messages: list[dict],
                 json_schema: dict | None = None, temperature: float = 0.0): ...


class NarrationSentence(BaseModel):
    text: str
    stat_ids: list[str] = Field(default_factory=list)


class Narration(BaseModel):
    """Gate outcome: accepted narrative plus the rejects, with reasons. Nothing vanishes."""

    accepted: list[NarrationSentence]
    rejected: list[dict]  # {"text", "stat_ids", "reason"}

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.accepted)


def gate_sentences(raw: list[NarrationSentence], stats: dict[str, Stat]) -> Narration:
    """Deterministic acceptance. Pure function — unit-tested without any LLM."""
    accepted: list[NarrationSentence] = []
    rejected: list[dict] = []
    for s in raw:
        if not s.stat_ids:
            rejected.append({**s.model_dump(), "reason": "cites no stat ids"})
            continue
        missing = [sid for sid in s.stat_ids if sid not in stats]
        if missing:
            rejected.append({**s.model_dump(), "reason": f"unknown stat ids: {missing}"})
            continue
        loose = verify_groundedness(s.text, stats)
        if loose:
            rejected.append({**s.model_dump(), "reason": f"ungrounded numbers: {loose}"})
            continue
        accepted.append(s)
    return Narration(accepted=accepted, rejected=rejected)


def narrate(
    gateway: CompletesJson, model: str, brief_markdown: str, stats: dict[str, Stat]
) -> Narration:
    """One gateway call, strict JSON schema, then the deterministic gate."""
    if not model:
        raise RuntimeError(
            "narration model is not set (LLM_MODEL_EXTRACTION). Refusing to guess a model.")
    stat_list = "\n".join(f"- {sid} = {fmt(s.value)} ({s.name})"
                          for sid, s in sorted(stats.items()))
    result = gateway.complete(
        model=model,
        messages=[
            {"role": "system",
             "content": ("Rewrite the project brief below as a short executive narrative "
                         "of 3 to 6 sentences. HARD RULES: every sentence must list, in "
                         "stat_ids, the ids from the stat list that support it; use ONLY "
                         "numbers that appear verbatim in the stat list (same formatting); "
                         "never invent a number, a workstream, or a stat id. Return JSON.")},
            {"role": "user",
             "content": f"STAT LIST:\n{stat_list}\n\nBRIEF:\n{brief_markdown}"},
        ],
        json_schema=NARRATION_SCHEMA,
    )
    if isinstance(result, list):  # envelope quirk seen live on some providers
        result = {"sentences": result}
    raw = [NarrationSentence.model_validate(item) for item in result.get("sentences", [])]
    return gate_sentences(raw, stats)
