FROM node:22-alpine AS frontend-build

WORKDIR /build/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
ENV VITE_API_URL=/api/v1
RUN pnpm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir .
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations

COPY --from=frontend-build /build/frontend/dist /app/frontend-dist

EXPOSE 7860

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 7860"]
