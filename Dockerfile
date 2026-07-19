FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /opt/termloop

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

RUN useradd -m -u 1000 termloop && mkdir -p /data && chown termloop:termloop /data
USER termloop

VOLUME /data

CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
