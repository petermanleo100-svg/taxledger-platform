FROM python:3.12-slim
WORKDIR /app
RUN addgroup --system taxledger && adduser --system --ingroup taxledger --home /app taxledger
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
RUN mkdir -p /app/work && chown -R taxledger:taxledger /app
USER taxledger
EXPOSE 8000
CMD ["uvicorn","taxledger.api:create_app","--factory","--host","0.0.0.0","--port","8000"]
