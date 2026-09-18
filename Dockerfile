FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOST=0.0.0.0 DATA_DIR=/data CAPTION_FONT="Noto Sans Devanagari"
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-noto-core fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY assets ./assets
COPY docs/client-prompts.txt ./docs/client-prompts.txt
COPY run.py ./
EXPOSE 8080
CMD ["python", "run.py"]
