# Local container recipe only; no deployment is configured.
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && useradd --create-home appuser
COPY app.py config.py ./
COPY templates ./templates
COPY LICENSE UPSTREAM.md ./
COPY LICENSES ./LICENSES
USER appuser
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "120", "app:app"]
