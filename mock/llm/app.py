"""mock-llm — OpenAI-compatible /v1/chat/completions.

Behavior depends on LLM_ADVERSARIAL:
  - 1 (default): if the caller asks for structured output (JSON in the prompt,
    response_format={"type":"json_object"}, or function/tool calling), respond
    with a clean JSON object. Otherwise respond with chatty prose where the
    answer is buried in natural language. Tests whether the caller's prompt
    pins the output shape.
  - 0: always respond with the clean JSON shape. Easier mode.

This service is deterministic and offline; no real API keys involved.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import time
import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

LLM_ADVERSARIAL: bool = os.environ.get("LLM_ADVERSARIAL", "1") == "1"
MIN_LATENCY_MS = 800
MAX_LATENCY_MS = 1500

app = FastAPI(title="mock-llm")


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True}


@app.get("/v1/info")
def info() -> dict[str, Any]:
    return {"adversarial": LLM_ADVERSARIAL}


class ChatMessage(BaseModel):
    role: str
    content: str | None = None


class ChatRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[ChatMessage]
    response_format: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = None
    max_tokens: int | None = None


# ---------- decision logic ----------
_STRUCTURED_HINTS = re.compile(
    r"\b(json|structured|schema|object\s+with\s+keys|respond\s+with\s+a\s+(json|object)|"
    r"return\s+(only\s+)?(a\s+)?json|format[:\s]+json|valid\s+json)\b",
    re.IGNORECASE,
)


def caller_asked_for_structure(req: ChatRequest) -> bool:
    if req.response_format and req.response_format.get("type") in (
        "json_object",
        "json_schema",
    ):
        return True
    if req.tools:
        return True
    blob = " ".join(m.content or "" for m in req.messages)
    return bool(_STRUCTURED_HINTS.search(blob))


# ---------- canned answers ----------
_STRUCTURED_ANSWER = {
    "start_seconds": 75,
    "end_seconds": 120,
    "reason": (
        "Highest emotional spike of the video — host pivots from calm "
        "exploration to a panicked discovery, then directly stages the "
        "biggest payoff (the Ferris wheel moving on its own)."
    ),
    "confidence": 0.86,
}

_PROSE_ANSWER = (
    "Looking through the transcript, the moment I'd pull is roughly around "
    "the one minute fifteen second mark — that's when the host suddenly stops "
    "and reacts to a noise, and then the Ferris wheel sequence kicks off. "
    "It runs through to about two minutes, give or take. Honestly the chunk "
    "from 75 to 120 seconds is your money shot, though the lead-in at 60 is "
    "decent context if you've got room."
)


def _shape_response(content: str, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": 80,
            "total_tokens": 280,
        },
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest) -> dict[str, Any]:
    # mimic LLM latency
    await asyncio.sleep(random.uniform(MIN_LATENCY_MS, MAX_LATENCY_MS) / 1000.0)

    asked_structured = caller_asked_for_structure(req)
    if not LLM_ADVERSARIAL or asked_structured:
        content = json.dumps(_STRUCTURED_ANSWER)
    else:
        content = _PROSE_ANSWER

    return _shape_response(content, req.model)
