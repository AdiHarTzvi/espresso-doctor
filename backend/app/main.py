"""FastAPI backend for Espresso Doctor.

Run from the project folder:  .venv/bin/uvicorn backend.app.main:app --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic_ai.models import Model

from .agent import diagnose_shot, looks_like_instructions
from .config import PROJECT_DIR, Settings, get_settings
from .db import Database
from .progress import compute_progress
from .schemas import ShotIn

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"


def _shot_or_404(db: Database, shot_id: int) -> dict:
    shot = db.get_shot(shot_id)
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    return shot


def create_app(settings: Settings | None = None, model_override: Model | None = None) -> FastAPI:
    """`model_override` lets tests run the real agent against an offline PydanticAI test model."""
    settings = settings or get_settings()
    db = Database(settings.db_path)
    ai_slots = asyncio.Semaphore(2)  # at most two AI runs at once

    app = FastAPI(title="Espresso Doctor", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.state.db = db
    app.state.settings = settings

    @app.exception_handler(RequestValidationError)
    async def readable_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        messages = []
        for err in exc.errors():
            field = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            msg = err.get("msg", "invalid value").removeprefix("Value error, ")
            messages.append(f"{field}: {msg}" if field else msg)
        return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})

    @app.get("/api/health")
    def health() -> dict:
        # Deliberately reports only whether a key exists, never its value.
        return {
            "status": "ok",
            "model": settings.model,
            "provider": settings.provider,
            "api_key_configured": settings.api_key_configured or model_override is not None,
            "pricing_known": settings.price_input_per_1m is not None,
            "custom_base_url": settings.base_url is not None,
        }

    @app.get("/api/shots")
    def list_shots(limit: int = 100) -> list[dict]:
        diagnosed = db.diagnosed_shot_ids()
        return [{**s, "has_diagnosis": s["id"] in diagnosed} for s in db.list_shots(limit=limit)]

    @app.post("/api/shots", status_code=201)
    def create_shot(shot: ShotIn) -> dict:
        return db.add_shot(shot)

    @app.get("/api/shots/{shot_id}")
    def get_shot(shot_id: int) -> dict:
        shot = _shot_or_404(db, shot_id)
        flagged = looks_like_instructions(shot.get("notes")) or looks_like_instructions(shot.get("grind_setting"))
        return {**shot, "diagnosis": db.latest_diagnosis(shot_id), "safety_flags": ["notes_look_like_instructions"] if flagged else []}

    @app.delete("/api/shots/{shot_id}", status_code=204)
    def delete_shot(shot_id: int) -> None:
        if not db.delete_shot(shot_id):
            raise HTTPException(status_code=404, detail="Shot not found")

    @app.post("/api/shots/{shot_id}/diagnose")
    async def diagnose(shot_id: int) -> JSONResponse:
        shot = _shot_or_404(db, shot_id)
        if model_override is None and not settings.api_key_configured:
            raise HTTPException(
                status_code=503,
                detail="No AI key found. Add PORTKEY_API_KEY (or OPENAI_API_KEY) to .env (see README) and restart the backend.",
            )
        async with ai_slots:
            outcome = await diagnose_shot(db, shot, settings, model=model_override)
        usage = outcome.usage
        model_name = f"{settings.model} via {settings.provider}" if model_override is None else f"test:{type(model_override).__name__}"
        diag_id = db.add_diagnosis(
            shot_id=shot_id,
            status="ok" if outcome.ok else "error",
            model=model_name,
            result=outcome.result.model_dump() if outcome.result else None,
            error=outcome.error,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            cost_usd=outcome.cost_usd,
            tools_used=outcome.tools_used,
        )
        body = {
            "id": diag_id,
            "shot_id": shot_id,
            "ok": outcome.ok,
            "result": outcome.result.model_dump() if outcome.result else None,
            "error": outcome.error,
            "safety_flags": outcome.safety_flags,
            "tools_used": outcome.tools_used,
            "usage": {
                "model": model_name,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cached_input_tokens": usage.cache_read_tokens,
                "requests": usage.requests,
                "tool_calls": usage.tool_calls,
                "cost_usd": outcome.cost_usd,
            },
        }
        return JSONResponse(status_code=200 if outcome.ok else 502, content=body)

    @app.get("/api/progress")
    def progress() -> dict:
        return compute_progress(db.list_shots(limit=200))

    @app.get("/api/usage")
    def usage_summary() -> dict:
        return {**db.usage_summary(), "model": settings.model}

    # Optional: serve the built frontend (npm run build) from the same server.
    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            candidate = (FRONTEND_DIST / path).resolve()
            if path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
