"""Request/response models. Validation here is the first safety layer: unreasonable
numbers are rejected before anything reaches the database or the AI agent."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Taste = Literal["sour", "bitter", "balanced", "weak", "other"]

# Generous but realistic home-espresso ranges.
DOSE_MIN, DOSE_MAX = 5.0, 30.0       # grams of ground coffee
YIELD_MIN, YIELD_MAX = 5.0, 120.0    # grams of liquid espresso
TIME_MIN, TIME_MAX = 5.0, 120.0      # seconds
RATIO_MIN, RATIO_MAX = 0.5, 6.0      # yield / dose
NOTES_MAX = 500
GRIND_MAX = 40

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(value: str | None, max_len: int) -> str | None:
    """Strip control characters and surrounding whitespace; empty -> None."""
    if value is None:
        return None
    value = _CONTROL_CHARS.sub("", value).strip()
    if len(value) > max_len:
        raise ValueError(f"must be at most {max_len} characters")
    return value or None


class ShotIn(BaseModel):
    dose_g: float = Field(ge=DOSE_MIN, le=DOSE_MAX, description="Coffee dose in grams")
    yield_g: float = Field(ge=YIELD_MIN, le=YIELD_MAX, description="Espresso yield in grams")
    time_s: float = Field(ge=TIME_MIN, le=TIME_MAX, description="Extraction time in seconds")
    grind_setting: str | None = Field(default=None, description="Optional grinder setting, e.g. '12' or '2.5'")
    taste: Taste
    notes: str | None = None

    @field_validator("grind_setting")
    @classmethod
    def _grind(cls, v: str | None) -> str | None:
        return clean_text(v, GRIND_MAX)

    @field_validator("notes")
    @classmethod
    def _notes(cls, v: str | None) -> str | None:
        return clean_text(v, NOTES_MAX)

    @model_validator(mode="after")
    def _ratio(self) -> "ShotIn":
        ratio = self.yield_g / self.dose_g
        if not RATIO_MIN <= ratio <= RATIO_MAX:
            raise ValueError(
                f"yield/dose ratio 1:{ratio:.2f} is outside the plausible range 1:{RATIO_MIN}–1:{RATIO_MAX}; "
                "check that dose and yield were entered in grams"
            )
        return self


class Shot(ShotIn):
    id: int
    created_at: str
    brew_ratio: float


# ---- Agent output -------------------------------------------------------------------

Variable = Literal["grind", "dose", "yield", "time", "temperature", "puck_prep", "none"]


class Adjustment(BaseModel):
    variable: Variable = Field(description="The ONE variable to change for the next shot")
    action: str = Field(max_length=200, description="Concrete instruction, e.g. 'Grind 1 step finer'")
    target: str | None = Field(
        default=None, max_length=160, description="Optional target for the next shot, e.g. '18 g in -> 36 g out in 28-32 s'"
    )


class Diagnosis(BaseModel):
    """Structured output of the Espresso Doctor agent."""

    diagnosis: str = Field(max_length=600, description="Most likely explanation, phrased as a hypothesis")
    recommended_adjustment: Adjustment
    explanation: str = Field(max_length=1200, description="Why this change should help, referencing the user's own shots")
    facts: list[str] = Field(max_length=6, description="Observations taken directly from the recorded numbers or tool results")
    hypotheses: list[str] = Field(max_length=4, description="Possible causes that are NOT certain")
    confidence: Literal["low", "medium", "high"]
    uncertainty: str = Field(max_length=500, description="What is uncertain and what would change the recommendation")


class DiagnosisRecord(BaseModel):
    id: int
    shot_id: int
    created_at: str
    result: Diagnosis
    model: str
    input_tokens: int
    output_tokens: int
    requests: int
    tool_calls: int
    cost_usd: float | None
    tools_used: list[str]
