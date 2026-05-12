SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

# Load .env if present so docker-compose picks up overrides.
ifneq (,$(wildcard .env))
include .env
export
endif

MOCK_DISCORD_PORT ?= 7001
MOCK_PLATFORM_PORT ?= 7002
MOCK_LLM_PORT ?= 7003
URL ?= https://www.youtube.com/watch?v=dQw4w9WgXcQ

.PHONY: help dev down restart status send logs reset rebuild ps

help:
	@echo "the-discord-bot — mock environment"
	@echo ""
	@echo "Usage:"
	@echo "  make dev                 Start all mock services in the background"
	@echo "  make down                Stop all mock services"
	@echo "  make restart             Restart mock services"
	@echo "  make rebuild             Rebuild containers from scratch"
	@echo "  make status              Show service health + most recent interactions"
	@echo "  make send url=<URL>      Invoke /opus <url> (defaults to a sample URL)"
	@echo "  make logs                Tail the channel log as a chat view"
	@echo "  make reset               Clear channel history (keeps services up)"
	@echo "  make ps                  docker compose ps"
	@echo ""
	@echo "Endpoints:"
	@echo "  Discord  : http://localhost:$(MOCK_DISCORD_PORT)"
	@echo "  Platform : http://localhost:$(MOCK_PLATFORM_PORT)"
	@echo "  LLM      : http://localhost:$(MOCK_LLM_PORT)"

dev:
	docker compose up -d --build
	@echo ""
	@echo "Mock services starting. Tail logs with: make logs"
	@echo "Send a slash command:           make send url=https://youtube.com/watch?v=..."

down:
	docker compose down

restart:
	docker compose restart

rebuild:
	docker compose build --no-cache
	docker compose up -d

ps:
	docker compose ps

status:
	@bash scripts/status.sh

send:
	@bash scripts/send.sh "$(URL)"

logs:
	@python3 scripts/logs.py

reset:
	@curl -fsS -X POST http://localhost:$(MOCK_DISCORD_PORT)/v1/channel/reset >/dev/null && \
		echo "Channel history cleared."
