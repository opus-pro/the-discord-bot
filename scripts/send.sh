#!/usr/bin/env bash
# Send a /opus slash command to the mock Discord server.
#
# Usage:
#   bash scripts/send.sh                                   # sends to a default URL
#   bash scripts/send.sh https://youtube.com/watch?v=foo
#
# Environment:
#   MOCK_DISCORD_PORT (default 7001)

set -euo pipefail

URL="${1:-https://www.youtube.com/watch?v=dQw4w9WgXcQ}"
PORT="${MOCK_DISCORD_PORT:-7001}"
ENDPOINT="http://localhost:${PORT}/v1/commands/send"

PAYLOAD=$(printf '{"name":"opus","options":{"url":"%s"}}' "$URL")

echo "→ POST ${ENDPOINT}"
echo "  /opus url=${URL}"
echo

RESPONSE=$(curl -sS -X POST "${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")

echo "${RESPONSE}" | python3 -m json.tool
