# workspace/

This is your folder. Build the bot here, in any language, with any deps.

The mock environment lives one directory up; you should not need to edit
anything outside `workspace/`. Treat `mock/` as an external system you're
integrating against — same way you'd treat the real Discord API in
production.

## What you need to know

1. Your bot must accept HTTP POSTs at `http://localhost:8080/interactions`
   (default; override via `BOT_WEBHOOK_URL` in `.env`).
2. The full API contract for the three mock services is in
   [`../docs/PROTOCOL.md`](../docs/PROTOCOL.md).
3. The product spec / business context is in
   [`../README.md`](../README.md).
4. When something feels wrong: [`../docs/HINTS.md`](../docs/HINTS.md).

## Useful commands while you work

```bash
make dev                  # boot the mocks
make logs                 # tail the channel (run in a separate terminal)
make send url=<yt-url>    # invoke /opus
make status               # health + recent interactions
make reset                # wipe channel state
```

Good luck. Have fun with it.
