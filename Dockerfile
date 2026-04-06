FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
COPY setup.py pyproject.toml README.md README-Krionis-pipeline.md MANIFEST.in ./
COPY rag_llm_api_pipeline ./rag_llm_api_pipeline
COPY config ./config
COPY rag_orchestrator ./rag_orchestrator

RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt && \
    python -m pip install -e . && \
    python -m pip install -e ./rag_orchestrator

RUN mkdir -p /app/data/manuals /app/data/reviews /app/data/feedback /app/data/audit /app/indices

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "rag_llm_api_pipeline.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
