FROM python:3.11-slim

WORKDIR /app

# Instala dependências mínimas do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos do projeto
COPY . /app

# Expõe a porta 8080 (usada pelo Render/Railway/Fly.io)
EXPOSE 8080

# Inicia apenas o servidor de sinalização e arquivos estáticos (modo servidor de nuvem)
CMD ["python", "main.py", "--no-browser"]
