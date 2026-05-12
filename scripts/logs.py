#!/usr/bin/env python3
"""Render the mock Discord channel log as a chat view, then tail for new messages.

Polls mock-discord every second by default. Ctrl-C to exit.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
import urllib.request
from datetime import datetime
from typing import Any

PORT = int(os.environ.get("MOCK_DISCORD_PORT", "7001"))
URL = f"http://localhost:{PORT}/v1/channel/messages"
POLL_SECONDS = 1.0


def fetch_messages() -> list[dict[str, Any]]:
    with urllib.request.urlopen(URL, timeout=2) as resp:
        body = json.loads(resp.read())
    return body.get("messages", [])


def fmt_time(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M:%S")


def fmt_options(options: dict[str, Any]) -> str:
    if not options:
        return ""
    return " ".join(f"{k}={v}" for k, v in options.items())


def render(event: dict[str, Any]) -> str:
    t = fmt_time(event.get("ts_ms", 0))
    typ = event.get("type", "")
    iid = event.get("interaction_id", "")[:8]

    if typ == "user.command":
        opts = fmt_options(event.get("options") or {})
        return f"[{t}] [{iid}] 👤  user invoked  {event['command']} {opts}".rstrip()

    if typ == "bot.message":
        ack = event.get("ack_ms", "?")
        return (
            f"[{t}] [{iid}] ✅  bot ack'd in {ack}ms (immediate)\n"
            f"            🤖  {event.get('content', '')}"
        )

    if typ == "bot.deferred":
        ack = event.get("ack_ms", "?")
        return f"[{t}] [{iid}] ⏳  bot ack'd in {ack}ms (deferred — 'thinking...')"

    if typ == "bot.followup":
        prefix = "🔁  bot edited deferred reply" if event.get("edits_deferred_placeholder") else "🤖  bot followup"
        content = event.get("content", "") or ""
        att = event.get("attachments") or []
        embeds = event.get("embeds") or []
        out = [f"[{t}] [{iid}] {prefix}"]
        if content:
            out.append(f"            {content}")
        for e in embeds:
            title = e.get("title", "")
            url = e.get("url", "")
            out.append(f"            ┃ embed: {title} {url}".rstrip())
        for a in att:
            out.append(f"            ┃ attachment: {a.get('url') or a.get('filename', '?')}")
        return "\n".join(out)

    if typ == "interaction.timeout":
        ms = event.get("deadline_ms", "?")
        return (
            f"[{t}] [{iid}] ❌  Interaction failed — bot did not ACK within {ms}ms.\n"
            f"            (any follow-ups for this interaction will be rejected)"
        )

    if typ == "interaction.unreachable":
        return f"[{t}] [{iid}] ⚠️   Bot unreachable: {event.get('error', '')}\n            URL: {event.get('bot_webhook_url', '?')}"

    if typ == "interaction.bad_status":
        return f"[{t}] [{iid}] ⚠️   Bot returned HTTP {event.get('http_status')}: {event.get('body', '')[:120]}"

    if typ == "interaction.non_json":
        return f"[{t}] [{iid}] ⚠️   Bot response was not JSON: {event.get('body', '')[:120]}"

    if typ == "interaction.invalid_type":
        return (
            f"[{t}] [{iid}] ⚠️   Bot returned response type={event.get('received_type')}; "
            "expected 4 (CHANNEL_MESSAGE_WITH_SOURCE) or 5 (DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)"
        )

    return f"[{t}] [{iid}] ?  {typ}: {json.dumps(event)}"


def main() -> int:
    print(f"# Tailing channel from {URL}  (Ctrl-C to quit)")
    print("# ─────────────────────────────────────────────────────────────")
    seen = 0

    def _handle_sigint(_sig, _frame):
        print("\n# bye")
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    while True:
        try:
            messages = fetch_messages()
        except Exception as e:  # noqa: BLE001
            print(f"# (cannot reach {URL}: {e})", file=sys.stderr)
            time.sleep(POLL_SECONDS)
            continue

        for ev in messages[seen:]:
            print(render(ev))
        seen = len(messages)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
