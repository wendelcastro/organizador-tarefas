FROM python:3.11-slim

# Instalar ffmpeg para conversao de audio
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependencias primeiro (cache do Docker)
COPY bot/requirements.txt ./bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt

# Copiar codigo do bot
COPY bot/ ./bot/

# O .env sera configurado via variaveis de ambiente do host
# NAO copie o .env para a imagem!

# Porta do health check (Koyeb usa PORT=8000 por padrao)
EXPOSE 8000

CMD ["python", "bot/main.py"]
