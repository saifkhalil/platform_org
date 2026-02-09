FROM python:3.11-slim

WORKDIR /app

RUN pip install -U uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* /app/

# Create venv outside /app so it is not shadowed by volume mounts
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv sync --no-dev

ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . /app

CMD ["python", "-m", "uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
