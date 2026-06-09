# DocLite backend — standalone image for Northflank (or any container host).
# Builds ONLY the FastAPI app (no frontend). Binds to $PORT (default 8000).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DOCLITE_DATABASE_URL=sqlite:////data/doclite.db \
    DOCLITE_SEED_ON_STARTUP=true

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# App source.
COPY . .

# SQLite lives here; mount a Northflank persistent volume at /data to keep data
# across redeploys (otherwise it resets each deploy — demo users are re-seeded).
RUN mkdir -p /data

EXPOSE 8000

# Lightweight container healthcheck against the API.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request,sys; \
urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/health'); sys.exit(0)" \
  || exit 1

# Shell form so ${PORT} is expanded (Northflank may inject its own PORT).
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
