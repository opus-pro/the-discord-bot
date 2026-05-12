"""mock-platform — emulates two internal OpusClip APIs:

1. Agent Opus video pipeline (POST /v1/clip + GET /v1/clip/{id})
2. YouTube transcript proxy (GET /v1/transcript)
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from transcripts import DEFAULT_TRANSCRIPT

PLATFORM_DELAY_SECONDS: float = float(os.environ.get("PLATFORM_DELAY_SECONDS", "60"))

JOBS: dict[str, dict[str, Any]] = {}

_http: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http
    _http = httpx.AsyncClient(timeout=10.0)
    try:
        yield
    finally:
        await _http.aclose()


app = FastAPI(title="mock-platform", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True}


@app.get("/v1/info")
def info() -> dict[str, Any]:
    return {
        "platform_delay_seconds": PLATFORM_DELAY_SECONDS,
        "jobs_seen": len(JOBS),
    }


# ---------- video clip ----------
class CreateClipRequest(BaseModel):
    url: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    callback_url: str | None = Field(
        default=None,
        description="Optional. If set, mock-platform will POST the finished job here.",
    )


class CreateClipResponse(BaseModel):
    job_id: str
    status: str
    eta_seconds: float


async def _process_job(job_id: str) -> None:
    job = JOBS[job_id]
    await asyncio.sleep(PLATFORM_DELAY_SECONDS)

    job["status"] = "done"
    job["finished_at_ms"] = int(time.time() * 1000)
    job["video_url"] = f"https://cdn.opusclip-mock.local/{job_id}.mp4"

    callback_url = job.get("callback_url")
    if callback_url and _http is not None:
        try:
            await _http.post(
                callback_url,
                json={
                    "job_id": job_id,
                    "status": "done",
                    "video_url": job["video_url"],
                },
            )
            job["callback_status"] = "delivered"
        except httpx.HTTPError as e:
            job["callback_status"] = f"failed: {e}"


@app.post("/v1/clip", response_model=CreateClipResponse)
async def create_clip(req: CreateClipRequest, background_tasks: BackgroundTasks) -> CreateClipResponse:
    job_id = uuid.uuid4().hex[:16]
    JOBS[job_id] = {
        "id": job_id,
        "url": req.url,
        "start_seconds": req.start_seconds,
        "end_seconds": req.end_seconds,
        "callback_url": req.callback_url,
        "status": "processing",
        "created_at_ms": int(time.time() * 1000),
    }
    background_tasks.add_task(_process_job, job_id)
    return CreateClipResponse(
        job_id=job_id, status="processing", eta_seconds=PLATFORM_DELAY_SECONDS
    )


@app.get("/v1/clip/{job_id}")
def get_clip(job_id: str) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


# ---------- transcript ----------
@app.get("/v1/transcript")
def get_transcript(url: str = Query(...)) -> dict[str, Any]:
    return {"source_url": url, **DEFAULT_TRANSCRIPT}
