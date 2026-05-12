# When something isn't working

## "❌ Interaction failed" in `make logs`

mock-discord didn't get an HTTP 200 response from your bot within 3 seconds.

Likely causes:
- Your handler is doing real work (calling Agent Opus, hitting the LLM,
  rendering, etc.) inline before returning the HTTP response.
- Your handler is replying with a `type` other than `4` or `5`.
- Your handler is returning HTTP 500 or non-JSON.

Run `make status` to see how long the ACK took, or `curl http://localhost:7001/v1/interactions`
for the raw state of recent interactions.

## "⚠️ Bot unreachable" in `make logs`

mock-discord can't reach `BOT_WEBHOOK_URL`. By default it points at
`http://host.docker.internal:8080/interactions` — i.e. mock-discord (running
in Docker) trying to reach your bot (running on your laptop) at port 8080.

Two common fixes:
- Make sure your bot is actually listening on port 8080. Pick another port?
  copy `.env.example` to `.env`, change `BOT_WEBHOOK_URL`, and run
  `make restart`.
- On Linux, `host.docker.internal` is mapped via `extra_hosts: host-gateway`
  in `docker-compose.yml`. If you're on a weird Docker setup (rootless,
  Podman, WSL), you may need to set `BOT_WEBHOOK_URL=http://172.17.0.1:8080/interactions`
  or similar.

## My follow-up gets HTTP 404 "Unknown interaction (expired)"

The original interaction was marked expired (you blew the 3-second window).
Once an interaction expires, all follow-ups for it are rejected. Make sure
you're acknowledging fast enough.

## Port already in use

If 7001/7002/7003 collide with something on your laptop, change them in
`.env` and `make dev` again:

```
MOCK_DISCORD_PORT=17001
MOCK_PLATFORM_PORT=17002
MOCK_LLM_PORT=17003
```

## My LLM call returns prose instead of JSON

That's mock-llm's default adversarial behavior — it returns prose unless your
prompt asks for structured output. Either fix your prompt (recommended) or
set `LLM_ADVERSARIAL=0` in `.env` and `make restart`.

## I want to wait less for clip generation

Set `PLATFORM_DELAY_SECONDS=10` in `.env` and `make restart`. Production
latency is 30s–5min; the default 60s is a compromise. Don't set it to 0 — at
that point the only thing you're testing is whether your code can call an
endpoint, which is not what we're hiring for.

## Where do I see what the channel "looks like"?

`make logs` is a tail of the channel. Leave it running in a second terminal.
For the raw event stream, `curl -s http://localhost:7001/v1/channel/messages | jq`.

You can also poke each mock service interactively at its FastAPI docs page:

- mock-discord  : <http://localhost:7001/docs>
- mock-platform : <http://localhost:7002/docs>
- mock-llm      : <http://localhost:7003/docs>

## Reset between attempts

`make reset` clears the chat log and forgets all in-memory interactions
without bouncing the services. `make down && make dev` does a full restart
(and resets state via the recreated container).

## Mock services not starting

`make ps` shows what's up. `docker compose logs mock-discord` (etc.) for the
crash reason. `make rebuild` if you suspect a stale image.
