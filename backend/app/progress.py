"""Deterministic (non-AI) comparison of the latest shot with earlier shots.

"Improving" is judged from the user's own taste ratings, which is the only real quality signal the app
has. Ratio/time windows are shown as common rules of thumb, not as targets that define a good shot.
"""

from __future__ import annotations

from typing import Any

TASTE_SCORE = {"balanced": 2, "other": 1, "sour": 0, "bitter": 0, "weak": 0}
RULE_OF_THUMB = {"ratio_low": 1.5, "ratio_high": 2.5, "time_low": 25, "time_high": 35}


def _delta(a: float, b: float) -> float:
    return round(a - b, 2)


def compute_progress(shots_newest_first: list[dict[str, Any]]) -> dict[str, Any]:
    shots = list(reversed(shots_newest_first))  # oldest -> newest
    series = [
        {"id": s["id"], "created_at": s["created_at"], "brew_ratio": s["brew_ratio"], "time_s": s["time_s"],
         "taste": s["taste"], "grind_setting": s.get("grind_setting")}
        for s in shots[-30:]
    ]
    base: dict[str, Any] = {
        "total_shots": len(shots),
        "balanced_shots": sum(s["taste"] == "balanced" for s in shots),
        "rule_of_thumb": RULE_OF_THUMB,
        "series": series,
    }
    if len(shots) < 2:
        return {**base, "verdict": "not_enough_data", "verdict_text": "Record at least two shots to compare.",
                "latest": shots[-1] if shots else None, "previous": None, "deltas": None}

    latest, previous = shots[-1], shots[-2]
    lt, pt = TASTE_SCORE[latest["taste"]], TASTE_SCORE[previous["taste"]]
    if lt > pt:
        verdict, text = "improving", f"Taste moved from {previous['taste']} to {latest['taste']}."
    elif lt < pt:
        verdict, text = "worse", f"Taste moved from {previous['taste']} to {latest['taste']}."
    elif latest["taste"] == "balanced":
        verdict, text = "steady", "Two balanced shots in a row - keep this recipe."
    elif latest["taste"] == previous["taste"]:
        verdict, text = "no_change", f"Still {latest['taste']} - the last change did not fix it yet."
    else:
        verdict, text = "changed", f"Taste changed from {previous['taste']} to {latest['taste']} (overshot?)."

    recent = shots[-5:]
    earlier = shots[-10:-5]
    rate = lambda group: round(sum(s["taste"] == "balanced" for s in group) / len(group), 2) if group else None  # noqa: E731
    return {
        **base,
        "verdict": verdict,
        "verdict_text": text,
        "latest": latest,
        "previous": previous,
        "deltas": {
            "dose_g": _delta(latest["dose_g"], previous["dose_g"]),
            "yield_g": _delta(latest["yield_g"], previous["yield_g"]),
            "time_s": _delta(latest["time_s"], previous["time_s"]),
            "brew_ratio": _delta(latest["brew_ratio"], previous["brew_ratio"]),
            "grind_changed": (latest.get("grind_setting") or "") != (previous.get("grind_setting") or ""),
        },
        "balanced_rate_last_5": rate(recent),
        "balanced_rate_previous_5": rate(earlier),
    }
