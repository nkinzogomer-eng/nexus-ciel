FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY pyproject.toml README.md ./
COPY nexus ./nexus
COPY policies ./policies
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --upgrade pip && pip install -e .
EXPOSE 8000
CMD ["uvicorn", "nexus.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
