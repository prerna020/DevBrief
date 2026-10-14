FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .

# Install dependencies into .venv
RUN uv sync --no-dev

# Copy application code
COPY . .

# Slim runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy the venv and app code from the builder stage
COPY --from=builder /app /app

# Place the virtualenv in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Default command for the API server
CMD ["uvicorn", "app.webhook.server:app", "--host", "0.0.0.0", "--port", "8000"]
