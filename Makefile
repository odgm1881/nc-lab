.PHONY: check backend-check frontend-check migrations-check requirements-check docker-build backup restore-test

check: backend-check frontend-check

backend-check:
	cd backend && uv run ruff check . && uv run pytest

frontend-check:
	cd frontend && npm run lint && npm run build

migrations-check:
	cd backend && uv run alembic upgrade head && uv run alembic check

requirements-check:
	cd backend && uv export --locked --no-dev --extra postgres --no-emit-project --format requirements-txt --output-file /tmp/nklab-requirements.lock && tail -n +3 requirements.lock > /tmp/nklab-requirements.current && tail -n +3 /tmp/nklab-requirements.lock > /tmp/nklab-requirements.generated && diff -u /tmp/nklab-requirements.current /tmp/nklab-requirements.generated

docker-build:
	docker compose -f backend/docker-compose.yml build

backup:
	cd backend && sh scripts/backup_postgres.sh

restore-test:
	cd backend && sh scripts/test_restore_postgres.sh "$(BACKUP_FILE)"
