"""SQLite storage for shots and AI diagnoses (standard library only)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .schemas import ShotIn

SCHEMA = """
CREATE TABLE IF NOT EXISTS shots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT    NOT NULL,
    dose_g        REAL    NOT NULL,
    yield_g       REAL    NOT NULL,
    time_s        REAL    NOT NULL,
    grind_setting TEXT,
    taste         TEXT    NOT NULL,
    notes         TEXT
);
CREATE TABLE IF NOT EXISTS diagnoses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    shot_id       INTEGER NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
    created_at    TEXT    NOT NULL,
    status        TEXT    NOT NULL,          -- 'ok' or 'error'
    result_json   TEXT,                      -- Diagnosis JSON when status = 'ok'
    error         TEXT,                      -- short, user-safe error message
    model         TEXT    NOT NULL,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    requests      INTEGER NOT NULL DEFAULT 0,
    tool_calls    INTEGER NOT NULL DEFAULT 0,
    cost_usd      REAL,
    tools_used    TEXT    NOT NULL DEFAULT '[]'
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- shots -----------------------------------------------------------------------

    @staticmethod
    def _shot_row(row: sqlite3.Row) -> dict[str, Any]:
        shot = dict(row)
        shot["brew_ratio"] = round(shot["yield_g"] / shot["dose_g"], 2)
        return shot

    def add_shot(self, shot: ShotIn) -> dict[str, Any]:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO shots (created_at, dose_g, yield_g, time_s, grind_setting, taste, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now_iso(), shot.dose_g, shot.yield_g, shot.time_s, shot.grind_setting, shot.taste, shot.notes),
            )
            shot_id = cur.lastrowid
        return self.get_shot(shot_id)  # type: ignore[return-value]

    def get_shot(self, shot_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM shots WHERE id = ?", (shot_id,)).fetchone()
        return self._shot_row(row) if row else None

    def list_shots(self, limit: int = 100, before_id: int | None = None) -> list[dict[str, Any]]:
        """Newest first. `before_id` returns only shots recorded before that shot."""
        limit = max(1, min(int(limit), 500))
        with self.connect() as conn:
            if before_id is None:
                rows = conn.execute("SELECT * FROM shots ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM shots WHERE id < ? ORDER BY id DESC LIMIT ?", (before_id, limit)
                ).fetchall()
        return [self._shot_row(r) for r in rows]

    def delete_shot(self, shot_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM shots WHERE id = ?", (shot_id,))
        return cur.rowcount > 0

    # ---- diagnoses -------------------------------------------------------------------

    def add_diagnosis(
        self,
        *,
        shot_id: int,
        status: str,
        model: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        requests: int = 0,
        tool_calls: int = 0,
        cost_usd: float | None = None,
        tools_used: list[str] | None = None,
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO diagnoses (shot_id, created_at, status, result_json, error, model, input_tokens, "
                "output_tokens, requests, tool_calls, cost_usd, tools_used) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    shot_id, now_iso(), status, json.dumps(result) if result else None, error, model,
                    input_tokens, output_tokens, requests, tool_calls, cost_usd, json.dumps(tools_used or []),
                ),
            )
            return cur.lastrowid  # type: ignore[return-value]

    @staticmethod
    def _diag_row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["result"] = json.loads(d.pop("result_json")) if d.get("result_json") else None
        d["tools_used"] = json.loads(d["tools_used"] or "[]")
        return d

    def latest_diagnosis(self, shot_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM diagnoses WHERE shot_id = ? AND status = 'ok' ORDER BY id DESC LIMIT 1", (shot_id,)
            ).fetchone()
        return self._diag_row(row) if row else None

    def diagnosed_shot_ids(self) -> set[int]:
        with self.connect() as conn:
            rows = conn.execute("SELECT DISTINCT shot_id FROM diagnoses WHERE status = 'ok'").fetchall()
        return {r[0] for r in rows}

    def usage_summary(self) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS runs, SUM(status = 'ok') AS ok_runs, COALESCE(SUM(input_tokens), 0) AS input_tokens, "
                "COALESCE(SUM(output_tokens), 0) AS output_tokens, SUM(cost_usd) AS cost_usd FROM diagnoses"
            ).fetchone()
            recent = conn.execute(
                "SELECT id, shot_id, created_at, status, model, input_tokens, output_tokens, requests, tool_calls, "
                "cost_usd, tools_used, error FROM diagnoses ORDER BY id DESC LIMIT 20"
            ).fetchall()
        summary = dict(row)
        summary["ok_runs"] = summary["ok_runs"] or 0
        summary["cost_usd"] = round(summary["cost_usd"], 6) if summary["cost_usd"] is not None else None
        summary["recent"] = [{**dict(r), "tools_used": json.loads(r["tools_used"] or "[]")} for r in recent]
        return summary
