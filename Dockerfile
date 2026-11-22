FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

COPY app/requirements.txt .
RUN pip install -r requirements.txt

COPY app/app.py .

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data && chown app:app /data
USER 10001

EXPOSE 8000

# python с PID 1 игнорирует SIGTERM, а SIGINT app.py обрабатывает
STOPSIGNAL SIGINT

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.getenv('PORT', '8000'), timeout=2)"]

CMD ["python", "app.py"]
