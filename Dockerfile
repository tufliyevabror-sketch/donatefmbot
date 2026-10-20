FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ALLOW_LAPTOP=1 \
    EXTERNAL_TUNNEL=1 \
    WEBAPP_HOST=0.0.0.0 \
    HF_PERSIST_DIR=/app/data

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl ffmpeg \
      tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus tesseract-ocr-uzb \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /usr/local/bin/cloudflared \
      https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
 && chmod +x /usr/local/bin/cloudflared

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip wheel \
 && pip install -r requirements.txt \
 && pip install huggingface_hub

COPY . .

RUN mkdir -p data logs \
 && chmod +x hf_entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/app/hf_entrypoint.sh"]
CMD ["python", "-u", "main.py"]
