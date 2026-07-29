FROM node:24-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build


FROM python:3.13-slim AS backend-build

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY backend/ /build/backend/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /build/backend


FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST_PATH=/app/frontend-dist

RUN useradd --create-home --uid 10001 dueflow
COPY --from=backend-build /opt/venv /opt/venv
COPY --chown=dueflow:dueflow backend/ /app/backend/
COPY --from=frontend-build --chown=dueflow:dueflow \
    /build/frontend/dist /app/frontend-dist

WORKDIR /app/backend
USER dueflow
EXPOSE 10000

CMD ["dueflow-deploy"]
