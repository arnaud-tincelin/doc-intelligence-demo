FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY src/backend/requirements.txt .

# Install dependencies using uv
RUN uv pip install --system --no-cache -r requirements.txt

# Copy backend code
COPY src/backend/ .

# Copy frontend into backend directory (for static serving)
COPY src/frontend/ ./frontend/

EXPOSE 8000

CMD ["gunicorn", "--workers", "2", "--timeout", "120", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "app:app"]
