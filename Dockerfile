FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app/

# Railway provides $PORT; default 8080 for local docker run
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers=2 --threads=4 --timeout=30 main:app
