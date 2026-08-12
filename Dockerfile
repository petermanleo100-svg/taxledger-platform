FROM python:3.12-slim
WORKDIR /app
RUN addgroup --system taxledger && adduser --system --ingroup taxledger --home /app taxledger
COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN pip install --no-cache-dir .
RUN mkdir -p /app/work && chown -R taxledger:taxledger /app
USER taxledger
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["python","-c","import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"]
CMD ["uvicorn","taxledger.api:create_app","--factory","--host","0.0.0.0","--port","8000"]
