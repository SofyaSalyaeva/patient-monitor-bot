FROM python:3.14-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install .

COPY app/ ./app/

RUN adduser --disabled-password --gecos "" appuser
USER appuser

CMD ["python", "-m", "app.main"]
