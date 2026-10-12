# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OLIST_DATA_DIR=/app/data/raw \
    OLIST_WAREHOUSE_PATH=/app/warehouse/olist.duckdb

WORKDIR /app

# non-root user
RUN useradd --create-home --uid 1000 appuser

COPY pyproject.toml README.md ./
COPY src ./src
COPY .streamlit ./.streamlit
RUN pip install ".[app,agent]"

RUN mkdir -p /app/data/raw /app/warehouse && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health').status==200 else 1)"

CMD ["streamlit", "run", "src/olist_bi/app/streamlit_app.py", "--server.address=0.0.0.0"]
