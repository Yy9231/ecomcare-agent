.PHONY: up down test eval model-check backend frontend

up:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && .venv/bin/ruff check app tests && .venv/bin/pytest
	cd frontend && pnpm run lint && pnpm run build

eval:
	cd backend && .venv/bin/python -m app.evaluation

model-check:
	cd backend && .venv/bin/python -m app.model_check

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload

frontend:
	cd frontend && pnpm run dev
