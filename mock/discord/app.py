"""mock-discord — emulates Discord's slash-command interaction protocol.

The protocol the candidate sees is essentially Discord's real one (with the same
3-second ACK deadline). The "user" side is driven by `make send`.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

# ---------- configuration ----------
BOT_WEBHOOK_URL: str = os.environ.get(
    "BOT_WEBHOOK_URL", "http://host.docker.internal:8080/interactions"
)
APP_ID: str = "mock-app-0001"
ACK_DEADLINE_SECONDS: float = 3.0

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHANNEL_LOG = DATA_DIR / "channel.jsonl"

# ---------- in-memory state ----------
INTERACTIONS: dict[str, dict[str, Any]] = {}
TOKEN_INDEX: dict[str, str] = {}  # interaction_token -> interaction_id


def now_ms() -> int:
    return int(time.time() * 1000)


def append_event(event: dict[str, Any]) -> None:
    event = {"ts_ms": now_ms(), **event}
    with CHANNEL_LOG.open("a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


# ---------- lifespan ----------
_http: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http
    _http = httpx.AsyncClient(timeout=ACK_DEADLINE_SECONDS)
    try:
        yield
    finally:
        await _http.aclose()


app = FastAPI(title="mock-discord", lifespan=lifespan)


# ---------- diagnostics ----------
@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True}


@app.get("/v1/info")
def info() -> dict[str, Any]:
    return {
        "app_id": APP_ID,
        "bot_webhook_url": BOT_WEBHOOK_URL,
        "ack_deadline_ms": int(ACK_DEADLINE_SECONDS * 1000),
        "interactions_seen": len(INTERACTIONS),
    }


# ---------- send a slash command (driven by `make send`) ----------
class SendCommandRequest(BaseModel):
    name: str = "opus"
    options: dict[str, str] = Field(default_factory=dict)


@app.post("/v1/commands/send")
async def send_command(req: SendCommandRequest) -> dict[str, Any]:
    """Pretend a user typed `/<name> [options]` in the channel."""
    assert _http is not None

    interaction_id = uuid.uuid4().hex[:16]
    interaction_token = uuid.uuid4().hex
    interaction: dict[str, Any] = {
        "id": interaction_id,
        "token": interaction_token,
        "name": req.name,
        "options": dict(req.options),
        "status": "pending",
        "ack_kind": None,
        "ack_ms": None,
        "created_at_ms": now_ms(),
        "first_followup_seen": False,
    }
    INTERACTIONS[interaction_id] = interaction
    TOKEN_INDEX[interaction_token] = interaction_id

    append_event(
        {
            "type": "user.command",
            "interaction_id": interaction_id,
            "command": f"/{req.name}",
            "options": dict(req.options),
        }
    )

    payload = {
        "type": 2,  # APPLICATION_COMMAND
        "id": interaction_id,
        "token": interaction_token,
        "application_id": APP_ID,
        "data": {
            "name": req.name,
            "options": [{"name": k, "value": v} for k, v in req.options.items()],
        },
        "user": {"id": "u-tester", "username": "candidate-tester"},
        "channel_id": "general",
    }

    started = time.monotonic()
    try:
        resp = await _http.post(BOT_WEBHOOK_URL, json=payload)
    except (httpx.TimeoutException, httpx.ReadTimeout):
        interaction["status"] = "expired"
        append_event(
            {
                "type": "interaction.timeout",
                "interaction_id": interaction_id,
                "deadline_ms": int(ACK_DEADLINE_SECONDS * 1000),
            }
        )
        return {
            "id": interaction_id,
            "status": "timeout",
            "message": (
                f"Bot did not ACK within {int(ACK_DEADLINE_SECONDS * 1000)}ms. "
                "Discord would show 'Interaction failed' to the user."
            ),
        }
    except httpx.HTTPError as e:
        interaction["status"] = "error"
        append_event(
            {
                "type": "interaction.unreachable",
                "interaction_id": interaction_id,
                "error": str(e),
                "bot_webhook_url": BOT_WEBHOOK_URL,
            }
        )
        return {
            "id": interaction_id,
            "status": "error",
            "message": f"Could not reach bot at {BOT_WEBHOOK_URL}: {e}",
        }

    elapsed_ms = int((time.monotonic() - started) * 1000)

    if resp.status_code != 200:
        interaction["status"] = "error"
        append_event(
            {
                "type": "interaction.bad_status",
                "interaction_id": interaction_id,
                "http_status": resp.status_code,
                "body": resp.text[:500],
            }
        )
        return {
            "id": interaction_id,
            "status": "error",
            "message": f"Bot returned HTTP {resp.status_code}: {resp.text[:200]}",
        }

    try:
        body = resp.json()
    except json.JSONDecodeError:
        interaction["status"] = "error"
        append_event(
            {
                "type": "interaction.non_json",
                "interaction_id": interaction_id,
                "body": resp.text[:500],
            }
        )
        return {
            "id": interaction_id,
            "status": "error",
            "message": "Bot response was not JSON.",
        }

    response_type = body.get("type")
    if response_type == 4:
        # CHANNEL_MESSAGE_WITH_SOURCE
        interaction["status"] = "acked_immediate"
        interaction["ack_kind"] = "immediate"
        interaction["ack_ms"] = elapsed_ms
        content = (body.get("data") or {}).get("content", "")
        append_event(
            {
                "type": "bot.message",
                "interaction_id": interaction_id,
                "kind": "immediate",
                "content": content,
                "ack_ms": elapsed_ms,
            }
        )
        return {
            "id": interaction_id,
            "status": "ok",
            "ack_kind": "immediate",
            "ack_ms": elapsed_ms,
        }

    if response_type == 5:
        # DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
        interaction["status"] = "acked_deferred"
        interaction["ack_kind"] = "deferred"
        interaction["ack_ms"] = elapsed_ms
        append_event(
            {
                "type": "bot.deferred",
                "interaction_id": interaction_id,
                "ack_ms": elapsed_ms,
            }
        )
        return {
            "id": interaction_id,
            "status": "ok",
            "ack_kind": "deferred",
            "ack_ms": elapsed_ms,
        }

    interaction["status"] = "error"
    append_event(
        {
            "type": "interaction.invalid_type",
            "interaction_id": interaction_id,
            "received_type": response_type,
        }
    )
    return {
        "id": interaction_id,
        "status": "error",
        "message": (
            f"Bot returned interaction response type={response_type}; "
            "expected 4 (CHANNEL_MESSAGE_WITH_SOURCE) or 5 (DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)"
        ),
    }


# ---------- bot follow-up endpoint (Discord-shaped) ----------
@app.post("/webhooks/{app_id}/{interaction_token}")
async def followup(app_id: str, interaction_token: str, request: Request):
    interaction_id = TOKEN_INDEX.get(interaction_token)
    if interaction_id is None:
        raise HTTPException(
            status_code=404,
            detail={"code": 10015, "message": "Unknown Webhook"},
        )
    interaction = INTERACTIONS[interaction_id]

    if interaction["status"] in ("expired", "error"):
        raise HTTPException(
            status_code=404,
            detail={"code": 10062, "message": "Unknown interaction (expired)"},
        )
    if interaction["status"] == "pending":
        raise HTTPException(
            status_code=400,
            detail={"code": 40060, "message": "Interaction has not been responded to"},
        )

    body = await request.json()
    content = body.get("content", "")
    embeds = body.get("embeds", [])
    attachments = body.get("attachments", [])

    is_first = interaction["ack_kind"] == "deferred" and not interaction.get(
        "first_followup_seen"
    )
    if is_first:
        interaction["first_followup_seen"] = True

    append_event(
        {
            "type": "bot.followup",
            "interaction_id": interaction_id,
            "content": content,
            "embeds": embeds,
            "attachments": attachments,
            "edits_deferred_placeholder": is_first,
        }
    )
    return {"id": uuid.uuid4().hex[:16], "channel_id": "general"}


# ---------- channel inspection ----------
@app.get("/v1/channel/messages")
def channel_messages() -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    if CHANNEL_LOG.exists():
        with CHANNEL_LOG.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return {"messages": messages}


@app.post("/v1/channel/reset")
def channel_reset() -> dict[str, Any]:
    if CHANNEL_LOG.exists():
        CHANNEL_LOG.unlink()
    INTERACTIONS.clear()
    TOKEN_INDEX.clear()
    return {"ok": True}


@app.get("/v1/interactions")
def list_interactions(limit: int = 20) -> dict[str, Any]:
    items = sorted(
        INTERACTIONS.values(), key=lambda i: i["created_at_ms"], reverse=True
    )[:limit]
    return {"interactions": items}


@app.get("/v1/interactions/{interaction_id}")
def get_interaction(interaction_id: str) -> dict[str, Any]:
    interaction = INTERACTIONS.get(interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="not found")
    return interaction
