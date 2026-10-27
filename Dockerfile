FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends chromium fonts-liberation && rm -rf /var/lib/apt/lists/*
RUN chromium --headless=new --no-sandbox --disable-dev-shm-usage --dump-dom about:blank 2>/dev/null | grep -q "<html>"
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1 CERAI_ESCRS_PROVIDER=local
CMD ["python", "start.py"]
