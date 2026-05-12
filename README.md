# /opus — Discord bot for community-led growth

> **Status:** spec'd, not built. Owner: Growth Eng. Target: 2 sprints.
> If this is the first time you've opened this repo, read this top-to-bottom
> once, then `make dev` and start in `workspace/`.

## Why now

Most of our power-user creators (the editors who ship 10+ shorts a week) are
hanging out in a handful of Discord servers — *MrBeast Editor Lounge*,
*Lapse*, *"Shorts Mafia"*, etc. Paid-social CPC for that audience is up 40%
QoQ, so growth wants a top-of-funnel that doesn't bleed cash.

A lightweight "drop a YouTube link, get a clip back" Discord bot is the wedge.
Zero friction, instant value, fits the meme-share culture of those servers.

## What we're building

A bot that responds to a single slash command:

```
/opus <youtube-url>
```

The flow when a user types it:

1. The bot **acknowledges immediately** so the user doesn't see Discord's
   dreaded *"This interaction failed"* red box.
2. The OpusClip pipeline generates a 30–60s "best moment" clip from that
   video.
3. The bot drops the result into the channel as a reply to the original
   command.

Has to feel snappy. If a user is staring at a frozen *"thinking…"* spinner for
5 minutes they will close the tab and we'll never see them again.

## Constraints our vendors / platforms force on us

These are not negotiable; they're how the underlying systems work.

- **Discord interaction protocol** — Discord is a fast-twitch chat product, so
  they kill any bot interaction that doesn't get an HTTP response within
  **3 seconds**. Their docs let you respond with a "deferred" placeholder
  (the *"… is thinking"* row) and finish the real reply via a follow-up
  webhook, which is what every nontrivial bot ends up doing. Full
  shape in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).
- **Agent Opus video pipeline** — internal API. Async. Real-world latency is
  30s to 5 min depending on input length. Returns a CDN URL when done.
  Supports both polling and webhook callbacks; pick whichever matches your
  taste. The local mock answers at `http://localhost:7002`.
- **Hosted LLM** — we have a deal with [redacted vendor]; the endpoint is
  OpenAI-compatible. Latency is variable. Local mock at
  `http://localhost:7003`.

## Phase 2 — actually capture the lead

Phase 1 ships the demo. Growth doesn't want us *just* dropping MP4s in chat
though — every clip we generate is a free user we never see again.

Once Phase 1 works: instead of attaching the video file in the followup,
**return a one-time URL to our marketing claim page**. The page already
exists at `https://opusclip.com/claim/{token}` (built by the website team —
don't worry about it). When a user clicks the link, they land on a
*"Sign up to download your clip"* wall: we capture email, spin up a free
account, and then let them download.

What you need to build for Phase 2 is the **API the claim page calls into**:

- A way for the worker to register a fresh, single-use token tied to a
  finished clip
- An endpoint the claim page hits to validate the token and (assuming the
  user is signed in / cookied) hand back the video URL
- Tokens should expire — marketing said 24 hours

How you store any of this is up to you.

## Phase 3 — pick a less boring 30 seconds

Real complaint pulled from `#feedback` last Tuesday:

> *"the bot picks the most random part of my videos lol, my intro literally
> explains the joke and it cut to me drinking water"*

Before kicking off the Agent Opus job, use the LLM to read the YouTube
transcript and pick a more interesting 30-second window. Then pass that
window into the Agent Opus call as `start_seconds` / `end_seconds`.

Helpful mock endpoints:
- `GET http://localhost:7002/v1/transcript?url=<yt-url>` — transcript with
  timestamps
- `POST http://localhost:7003/v1/chat/completions` — OpenAI-compatible LLM,
  no API key needed

## Out of scope

- Any web frontend — claim page is already live, so just publish the API.
- Real Discord OAuth or app-creation in the Discord developer portal.
- Production database / infra provisioning — use whatever you want locally.
- Payment, plan tiers, premium-only rate limiting.

## How to run

```bash
make dev                      # boot the 3 mock services in background
make logs                     # in another terminal: tail the chat as it happens
make send url=<youtube-url>   # invoke /opus from a simulated user
make status                   # health check + recent interactions
make down                     # stop everything
make reset                    # clear the chat log without restarting
```

Your code lives in `workspace/` — any language, any framework, any deps you
want. Your bot needs to be reachable at `http://localhost:8080/interactions`,
or override `BOT_WEBHOOK_URL` in a local `.env` (see `.env.example`).

For full API contracts: [`docs/PROTOCOL.md`](docs/PROTOCOL.md).
When something doesn't work: [`docs/HINTS.md`](docs/HINTS.md).

## Layout

```
the-discord-bot/
├── README.md              ← you are here
├── Makefile               ← entry points
├── docker-compose.yml     ← mock-discord + mock-platform + mock-llm
├── docs/
│   ├── PROTOCOL.md        ← API shape for all three mocks
│   └── HINTS.md           ← troubleshooting
├── mock/                  ← don't edit; this is the "production" we're integrating with
│   ├── discord/
│   ├── platform/
│   └── llm/
└── workspace/             ← your code goes here
```
