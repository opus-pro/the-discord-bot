#!/usr/bin/env bash
# Quick health + recent interactions overview.

set -euo pipefail

DISCORD_PORT="${MOCK_DISCORD_PORT:-7001}"
PLATFORM_PORT="${MOCK_PLATFORM_PORT:-7002}"
LLM_PORT="${MOCK_LLM_PORT:-7003}"

check() {
  local name=$1
  local port=$2
  if curl -fsS --max-time 2 "http://localhost:${port}/healthz" >/dev/null 2>&1; then
    echo "  ✅ ${name} (:${port})  up"
  else
    echo "  ❌ ${name} (:${port})  down"
  fi
}

echo "Service health:"
check "mock-discord " "${DISCORD_PORT}"
check "mock-platform" "${PLATFORM_PORT}"
check "mock-llm     " "${LLM_PORT}"
echo

if curl -fsS --max-time 2 "http://localhost:${DISCORD_PORT}/v1/info" >/dev/null 2>&1; then
  INFO=$(curl -fsS "http://localhost:${DISCORD_PORT}/v1/info")
  BOT_URL=$(echo "${INFO}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["bot_webhook_url"])')
  echo "Bot webhook URL configured in mock-discord:"
  echo "  ${BOT_URL}"
  echo
fi

if curl -fsS --max-time 2 "http://localhost:${DISCORD_PORT}/v1/interactions?limit=5" >/dev/null 2>&1; then
  echo "Last 5 interactions:"
  curl -fsS "http://localhost:${DISCORD_PORT}/v1/interactions?limit=5" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for i in data["interactions"]:
    print(f"  {i[\"id\"][:8]}  /{i[\"name\"]}  status={i[\"status\"]}  ack_ms={i.get(\"ack_ms\")}")
'
fi
