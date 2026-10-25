"""Settings (.env discovery) and the deterministic progress comparison."""

from __future__ import annotations

import pytest

from backend.app import config
from backend.app.progress import compute_progress
from backend.app.schemas import ShotIn

from .conftest import add


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "PRICE_INPUT_PER_1M", "PRICE_OUTPUT_PER_1M",
                 "PRICE_CACHED_INPUT_PER_1M", "OPENAI_REASONING_EFFORT", "ESPRESSO_DB_PATH", "PORTKEY_API_KEY",
                 "PORTKEY_MODEL", "PORTKEY_BASE_URL", "AI_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    project = tmp_path / "parent" / "espresso-doctor"
    project.mkdir(parents=True)
    monkeypatch.setattr(config, "ENV_CANDIDATES", (project / ".env", project.parent / ".env"))
    monkeypatch.setenv("ESPRESSO_DB_PATH", str(tmp_path / "x.db"))
    return project


def test_env_in_parent_directory_is_found(clean_env):
    (clean_env.parent / ".env").write_text("OPENAI_API_KEY=sk-parent\n")
    s = config.get_settings()
    assert s.api_key == "sk-parent" and s.model == config.DEFAULT_MODEL


def test_project_env_wins_over_parent(clean_env):
    (clean_env / ".env").write_text("OPENAI_API_KEY=sk-project\nOPENAI_MODEL=gpt-4o-mini\n")
    (clean_env.parent / ".env").write_text("OPENAI_API_KEY=sk-parent\nOPENAI_MODEL=gpt-5-nano\n")
    s = config.get_settings()
    assert s.api_key == "sk-project" and s.model == "gpt-4o-mini"
    assert s.provider == "openai" and s.price_input_per_1m is None  # no built-in price for gpt-4o-mini


def test_unedited_project_env_does_not_hide_parent_key(clean_env):
    """Copying .env.example without editing it must not override a real key one directory up."""
    (clean_env / ".env").write_text("OPENAI_API_KEY=sk-your-key-here\nOPENAI_MODEL=\n")
    (clean_env.parent / ".env").write_text("OPENAI_API_KEY=sk-parent\n")
    s = config.get_settings()
    assert s.api_key == "sk-parent" and s.model == config.DEFAULT_MODEL


def test_placeholder_key_alone_counts_as_missing(clean_env):
    (clean_env / ".env").write_text("OPENAI_API_KEY=sk-your-key-here\n")
    assert config.get_settings().api_key_configured is False


def test_shell_variable_wins_over_env_files(clean_env, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-shell")
    (clean_env / ".env").write_text("OPENAI_API_KEY=sk-project\n")
    assert config.get_settings().api_key == "sk-shell"


def test_portkey_key_is_preferred_and_uses_the_gateway(clean_env):
    (clean_env.parent / ".env").write_text("PORTKEY_API_KEY=pk-course\nOPENAI_API_KEY=sk-direct\n")
    s = config.get_settings()
    assert s.provider == "portkey" and s.api_key == "pk-course"
    assert s.base_url == "https://api.portkey.ai/v1" and s.model == "gpt-5.6-luna"
    assert s.price_input_per_1m == 0.20 and s.price_output_per_1m == 1.20 and s.key_env_name == "PORTKEY_API_KEY"


def test_openai_key_is_the_fallback(clean_env):
    (clean_env / ".env").write_text("OPENAI_API_KEY=sk-direct\n")
    s = config.get_settings()
    assert s.provider == "openai" and s.api_key == "sk-direct" and s.base_url is None and s.model == "gpt-5-mini"


def test_ai_provider_can_force_openai(clean_env, monkeypatch):
    (clean_env.parent / ".env").write_text("PORTKEY_API_KEY=pk-course\nOPENAI_API_KEY=sk-direct\n")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    s = config.get_settings()
    assert s.provider == "openai" and s.api_key == "sk-direct"


def test_portkey_model_is_configurable(clean_env, monkeypatch):
    (clean_env.parent / ".env").write_text("PORTKEY_API_KEY=pk-course\n")
    monkeypatch.setenv("PORTKEY_MODEL", "gpt-6-luna")
    s = config.get_settings()
    assert s.model == "gpt-6-luna" and (s.price_input_per_1m, s.price_output_per_1m) == (0.10, 0.50)


def test_no_env_file_means_no_key(clean_env):
    assert config.get_settings().api_key_configured is False


def test_custom_model_prices_via_env(clean_env, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "my-model")
    assert config.get_settings().estimate_cost(1000, 1000) is None
    monkeypatch.setenv("PRICE_INPUT_PER_1M", "1.0")
    monkeypatch.setenv("PRICE_OUTPUT_PER_1M", "4.0")
    assert config.get_settings().estimate_cost(1_000_000, 500_000) == 3.0


def test_control_characters_are_stripped():
    s = ShotIn(dose_g=18, yield_g=36, time_s=28, taste="sour", notes="  hi\x00\x07 there  ", grind_setting="   ")
    assert s.notes == "hi there" and s.grind_setting is None


def test_progress_needs_two_shots(db):
    assert compute_progress([])["verdict"] == "not_enough_data"
    add(db)
    assert compute_progress(db.list_shots())["verdict"] == "not_enough_data"


@pytest.mark.parametrize(
    ("prev", "latest", "verdict"),
    [("sour", "balanced", "improving"), ("balanced", "bitter", "worse"), ("balanced", "balanced", "steady"),
     ("sour", "sour", "no_change"), ("sour", "bitter", "changed")],
)
def test_progress_verdicts(db, prev, latest, verdict):
    add(db, taste=prev, time_s=20)
    add(db, taste=latest, time_s=27)
    p = compute_progress(db.list_shots())
    assert p["verdict"] == verdict and p["deltas"]["time_s"] == 7
    assert [s["taste"] for s in p["series"]] == [prev, latest]
