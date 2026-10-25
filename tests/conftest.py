"""Shared fixtures. Offline tests use PydanticAI's FunctionModel, a scripted stand-in for the LLM that
drives the REAL agent, tools, limits and database - only the model's replies are scripted."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import pytest

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

from backend.app.config import Settings  # noqa: E402
from backend.app.db import Database  # noqa: E402
from backend.app.schemas import ShotIn  # noqa: E402

FAKE_KEY = "sk-test-DO-NOT-LEAK-1234567890"

GOOD_DIAGNOSIS: dict[str, Any] = {
    "diagnosis": "The shot was likely under-extracted: it ran fast and tasted sour.",
    "recommended_adjustment": {"variable": "grind", "action": "Grind one step finer", "target": "18 g -> 36 g in 27-32 s"},
    "explanation": "A finer grind slows the flow and usually increases extraction.",
    "facts": ["Ratio was 1:2.00", "Time was 20 s"],
    "hypotheses": ["Grind may be too coarse", "Beans may be very fresh"],
    "confidence": "high",
    "uncertainty": "Bean roast and freshness are unknown.",
}


def make_settings(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = dict(
        provider="portkey",
        api_key=FAKE_KEY,
        model="gpt-5.6-luna",
        base_url="https://api.portkey.ai/v1",
        reasoning_effort=None,
        price_input_per_1m=0.20,
        price_cached_input_per_1m=0.02,
        price_output_per_1m=1.20,
        db_path=tmp_path / "test.db",
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def db(settings: Settings) -> Database:
    return Database(settings.db_path)


def add(db: Database, **kw: Any) -> dict[str, Any]:
    data = dict(dose_g=18, yield_g=36, time_s=28, taste="balanced", grind_setting="10", notes=None)
    data.update(kw)
    return db.add_shot(ShotIn(**data))


class Recorder:
    """Keeps every message list the model received, so tests can inspect exactly what the LLM saw."""

    def __init__(self) -> None:
        self.calls: list[list[ModelMessage]] = []
        self.tool_returns: dict[str, Any] = {}


def scripted_model(
    recorder: Recorder,
    diagnosis: dict[str, Any] | None = None,
    tool_args: dict[str, Any] | None = None,
) -> FunctionModel:
    """Model that (1) calls both tools, then (2) returns the structured diagnosis."""
    diagnosis = diagnosis or GOOD_DIAGNOSIS

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        recorder.calls.append(list(messages))
        for msg in messages:
            for part in getattr(msg, "parts", []):
                if isinstance(part, ToolReturnPart):
                    recorder.tool_returns[part.tool_name] = part.content
        if len(recorder.calls) == 1:
            return ModelResponse(parts=[
                ToolCallPart("calculate_brew_ratio", tool_args or {"dose_g": 18, "yield_g": 36}),
                ToolCallPart("get_shot_history", {"limit": 10}),
            ])
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, diagnosis)])

    return FunctionModel(fn)


def looping_model(recorder: Recorder) -> FunctionModel:
    """A misbehaving model that calls a tool forever and never answers."""

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        recorder.calls.append(list(messages))
        return ModelResponse(parts=[ToolCallPart("get_shot_history", {"limit": 10})])

    return FunctionModel(fn)


def raising_model(exc_factory: Callable[[], Exception]) -> FunctionModel:
    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise exc_factory()

    return FunctionModel(fn)


def chatty_model() -> FunctionModel:
    """Produces a very long text reply (huge token usage) instead of the structured output."""

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("espresso " * 20_000)])

    return FunctionModel(fn)
