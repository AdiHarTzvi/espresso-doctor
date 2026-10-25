"""Settings for Espresso Doctor.

The .env file may live in the project folder or one directory above it. Both are loaded,
the project folder first; variables already set in the shell always win.
Secrets are never logged or returned by the API.

Two ways to reach the model (both use the OpenAI Responses API through the OpenAI SDK):
- "portkey" (preferred when PORTKEY_API_KEY is set): the course-provided Portkey gateway at
  https://api.portkey.ai/v1, authenticated with `Authorization: Bearer <PORTKEY_API_KEY>`.
  This is the same setup that worked in HW5. Default model: gpt-5.6-luna.
- "openai" (fallback when only OPENAI_API_KEY is set): api.openai.com directly. Default model: gpt-5-mini.
Set AI_PROVIDER=openai or AI_PROVIDER=portkey to force one when both keys exist.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

PROJECT_DIR = Path(__file__).resolve().parents[2]  # espresso-doctor/
ENV_CANDIDATES = (PROJECT_DIR / ".env", PROJECT_DIR.parent / ".env")

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
DEFAULT_MODELS = {"portkey": "gpt-5.6-luna", "openai": "gpt-5-mini"}
DEFAULT_MODEL = DEFAULT_MODELS["openai"]

# Official OpenAI API list prices, USD per 1M tokens: (input, cached input, output).
# Source: https://developers.openai.com/api/docs/pricing (checked 2026-10-25; luna = short-context rates).
# These are OpenAI's direct-API prices; what the course's Portkey account is billed may differ.
# Override with PRICE_INPUT_PER_1M / PRICE_CACHED_INPUT_PER_1M / PRICE_OUTPUT_PER_1M.
KNOWN_PRICES: dict[str, tuple[float, float, float]] = {
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-5-mini": (0.25, 0.025, 2.00),
}

PLACEHOLDER_VALUES = {"", "sk-your-key-here", "your-portkey-api-key-here"}


def load_env_files() -> list[Path]:
    """Load .env files (project folder first, then parent). Returns the files that were found.

    Precedence per variable: shell environment > project .env > parent .env. Empty values and the
    .env.example placeholders are skipped, so a copied-but-unedited project .env cannot hide a real
    key stored one directory up.
    """
    found = []
    for path in ENV_CANDIDATES:
        if not path.is_file():
            continue
        found.append(path)
        for name, value in dotenv_values(path).items():
            value = (value or "").strip()
            if value in PLACEHOLDER_VALUES:
                continue
            if os.environ.get(name, "").strip() in PLACEHOLDER_VALUES:
                os.environ[name] = value
    return found


def _env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return None if value in PLACEHOLDER_VALUES else value


def _float_env(name: str) -> float | None:
    raw = _env(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@dataclass(frozen=True)
class Settings:
    provider: str                 # "portkey" or "openai"
    api_key: str | None           # key for the selected provider (never logged or returned)
    model: str
    base_url: str | None          # None -> api.openai.com
    reasoning_effort: str | None
    price_input_per_1m: float | None
    price_output_per_1m: float | None
    db_path: Path
    price_cached_input_per_1m: float | None = None
    # Hard limits on every diagnosis run (no unbounded loops, bounded cost).
    request_limit: int = 4
    tool_calls_limit: int = 4
    total_tokens_limit: int = 16_000
    max_output_tokens: int = 2_500
    timeout_seconds: float = 60.0
    history_limit: int = 10

    @property
    def api_key_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def key_env_name(self) -> str:
        return "PORTKEY_API_KEY" if self.provider == "portkey" else "OPENAI_API_KEY"

    def estimate_cost(self, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float | None:
        """Approximate USD cost at official list prices, or None when no price is known."""
        if self.price_input_per_1m is None or self.price_output_per_1m is None:
            return None
        cached = min(max(cached_tokens, 0), input_tokens) if self.price_cached_input_per_1m is not None else 0
        cached_price = self.price_cached_input_per_1m or 0.0
        return round(
            (input_tokens - cached) / 1_000_000 * self.price_input_per_1m
            + cached / 1_000_000 * cached_price
            + output_tokens / 1_000_000 * self.price_output_per_1m,
            6,
        )


def get_settings() -> Settings:
    load_env_files()
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

    portkey_key, openai_key = _env("PORTKEY_API_KEY"), _env("OPENAI_API_KEY")
    provider = (_env("AI_PROVIDER") or "").lower()
    if provider not in ("portkey", "openai"):
        provider = "portkey" if portkey_key or not openai_key else "openai"

    if provider == "portkey":
        api_key = portkey_key
        model = _env("PORTKEY_MODEL") or DEFAULT_MODELS["portkey"]
        base_url = _env("PORTKEY_BASE_URL") or PORTKEY_BASE_URL
    else:
        api_key = openai_key
        model = _env("OPENAI_MODEL") or DEFAULT_MODELS["openai"]
        base_url = _env("OPENAI_BASE_URL")

    known = KNOWN_PRICES.get(model, (None, None, None))
    price_in, price_cached, price_out = (
        _float_env("PRICE_INPUT_PER_1M"), _float_env("PRICE_CACHED_INPUT_PER_1M"), _float_env("PRICE_OUTPUT_PER_1M"),
    )
    effort = (os.getenv("OPENAI_REASONING_EFFORT", "low").strip().lower()) or None
    if effort in ("none", "off"):
        effort = None
    return Settings(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        reasoning_effort=effort,
        price_input_per_1m=price_in if price_in is not None else known[0],
        price_cached_input_per_1m=price_cached if price_cached is not None else known[1],
        price_output_per_1m=price_out if price_out is not None else known[2],
        db_path=Path(_env("ESPRESSO_DB_PATH") or PROJECT_DIR / "data" / "espresso.db"),
    )
