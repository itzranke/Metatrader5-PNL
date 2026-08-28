.PHONY: dev-api dev-web test lint migrate db-up db-down

dev-api:
	uvicorn apps.api.app.main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

test:
	pytest -q

lint:
	ruff check .

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(m)"

db-up:
	docker compose -f infra/docker-compose.dev.yml up -d

db-down:
	docker compose -f infra/docker-compose.dev.yml down
