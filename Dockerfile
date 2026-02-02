FROM python:3.14-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install .

COPY app/ ./app/

CMD ["python", "-m", "app.main"]
