# Mock service protocols

Three local services are launched by `make dev`:

| Service        | Port | What it pretends to be              |
| -------------- | ---- | ----------------------------------- |
| mock-discord   | 7001 | Discord interactions API            |
| mock-platform  | 7002 | Internal Agent Opus video API + a YouTube transcript proxy |
| mock-llm       | 7003 | OpenAI-compatible chat completions  |

All three are FastAPI processes. None require any API key.

---

## 1. mock-discord — `http://localhost:7001`

Implements the relevant subset of Discord's
[Interactions](https://discord.com/developers/docs/interactions/receiving-and-responding)
protocol. Uses the same JSON shape, the same response type numbers, and the
same hard 3-second deadline as production Discord.

### 1.1 Bot webhook (you implement this)

When `make send url=...` is run, mock-discord POSTs an interaction to whatever
URL `BOT_WEBHOOK_URL` is set to. Default:

```
http://host.docker.internal:8080/interactions
```

Override by exporting `BOT_WEBHOOK_URL` in your `.env` and re-running
`make dev`.

The body that arrives at your endpoint:

```json
{
  "type": 2,
  "id": "a1b2c3d4...",
  "token": "long-opaque-token",
  "application_id": "mock-app-0001",
  "data": {
    "name": "opus",
    "options": [
      {"name": "url", "value": "https://www.youtube.com/watch?v=..."}
    ]
  },
  "user": {"id": "u-tester", "username": "candidate-tester"},
  "channel_id": "general"
}
```

### 1.2 What you must reply with — within 3 seconds

mock-discord waits **3 seconds** for an HTTP 200 response from your bot. After
that the connection is dropped, the interaction is marked **expired**, and any
later follow-ups for it will be rejected with HTTP 404. You'll see
`❌ Interaction failed` in `make logs`.

The response body must be JSON, and `type` must be one of:

| `type` | Name                                  | Use it when                                   |
| ------ | ------------------------------------- | --------------------------------------------- |
| `4`    | `CHANNEL_MESSAGE_WITH_SOURCE`         | You already have the final answer to show.    |
| `5`    | `DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE`| You need more time. Edit it later via 1.3.    |

Examples:

```json
// type 4 — done immediately, this is what the user sees
{"type": 4, "data": {"content": "Hi! Try /opus <youtube url>."}}

// type 5 — show "thinking…" and finish later
{"type": 5}
```

### 1.3 Following up after a deferred response

After you respond with `type: 5`, you have 15 minutes to deliver the real
content via:

```
POST http://localhost:7001/webhooks/{application_id}/{interaction_token}
Content-Type: application/json

{
  "content": "Your clip is ready: https://...",
  "embeds":      [ ... ],
  "attachments": [ ... ]
}
```

`{interaction_token}` is the `token` from the original interaction body.
`{application_id}` is `mock-app-0001` (or just whatever you got — it isn't
strictly checked).

The first follow-up after a deferred ACK edits the *"thinking…"* placeholder
into your real reply. Subsequent follow-ups append additional messages.

### 1.4 Diagnostic endpoints (for inspecting state)

```
GET  /healthz                          # liveness
GET  /v1/info                          # configured bot URL + counters
GET  /v1/channel/messages              # full chat log as JSONL
GET  /v1/interactions                  # last N interactions and their state
GET  /v1/interactions/{id}             # single interaction's state
POST /v1/channel/reset                 # wipe history
POST /v1/commands/send                 # what `make send` calls
```

---

## 2. mock-platform — `http://localhost:7002`

Two separate APIs bundled in one process for convenience.

### 2.1 Agent Opus video pipeline

Create a clip job:

```
POST /v1/clip
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=...",
  "start_seconds": 75,                            // optional
  "end_seconds":   120,                           // optional
  "callback_url":  "http://host.docker.internal:8080/clips/done"  // optional
}
```

Response (immediate):

```json
{ "job_id": "abcdef...", "status": "processing", "eta_seconds": 60 }
```

Two ways to learn when it's done:

**Polling:**
```
GET /v1/clip/{job_id}
→ {"id": "...", "status": "processing", ...}
   ... later ...
→ {"id": "...", "status": "done", "video_url": "https://cdn.opusclip-mock.local/abcdef.mp4", ...}
```

**Webhook:** if you supplied `callback_url` in the create request,
mock-platform will `POST` it when the job finishes:

```json
{
  "job_id": "abcdef...",
  "status": "done",
  "video_url": "https://cdn.opusclip-mock.local/abcdef.mp4"
}
```

Default delay is `PLATFORM_DELAY_SECONDS=60` (env var, see `.env.example`).
Real production latency is 30s–5min; the mock defaults to 60s so you can
iterate without waiting forever, but it's deliberately long enough to expose
the difference between sync and async implementations.

### 2.2 YouTube transcript proxy

```
GET /v1/transcript?url=<youtube-url>
```

Returns:

```json
{
  "source_url": "...",
  "video_id": "ds-001",
  "title": "...",
  "duration_seconds": 240,
  "language": "en",
  "segments": [
    {"start": 0,  "end": 8,  "text": "..."},
    {"start": 8,  "end": 18, "text": "..."},
    ...
  ]
}
```

Returns the same fixture transcript regardless of input URL. The transcript
has timestamps and is ~4 minutes long.

---

## 3. mock-llm — `http://localhost:7003`

OpenAI-compatible chat completions.

```
POST /v1/chat/completions
Content-Type: application/json
# no Authorization header required

{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user",   "content": "..."}
  ],
  "response_format": {"type": "json_object"},   // optional
  "tools": [...],                                // optional
  "temperature": 0.2,                            // optional
  "max_tokens": 200                              // optional
}
```

Response shape matches OpenAI:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1717000000,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "..."},
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280}
}
```

Latency: 800–1500ms per request, randomized.

### Why my response doesn't parse

mock-llm has two response styles. It picks one based on whether your prompt
implies you want machine-readable output. If it does, you get a clean JSON
object. If it doesn't, you get prose. Set `LLM_ADVERSARIAL=0` in `.env` to
force the JSON style always (useful if you're stuck and want to debug the
rest of your pipeline).

---

## Diagnostic endpoints summary

```
GET http://localhost:7001/healthz   # mock-discord
GET http://localhost:7002/healthz   # mock-platform
GET http://localhost:7003/healthz   # mock-llm
GET http://localhost:7001/v1/info   # configured bot webhook URL
GET http://localhost:7002/v1/info   # configured platform delay
GET http://localhost:7003/v1/info   # adversarial flag state
```
