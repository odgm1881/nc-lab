.PHONY: check backend-check frontend-check migrations-check docker-build

check: backend-check frontend-check

backend-check:
	cd backend && uv run ruff check . && uv run pytest

frontend-check:
	cd frontend && npm run lint && npm run build

migrations-check:
	cd backend && uv run alembic upgrade head && uv run alembic check

docker-build:
	docker compose -f backend/docker-compose.yml build
