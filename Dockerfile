# Estágio 1: Base com Python
FROM python:3.10-slim

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia o arquivo de dependências e instala as bibliotecas
COPY requirements.txt .
RUN apt-get update && apt-get install -y curl && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# Copia os arquivos da aplicação para o diretório de trabalho
COPY . .

# Expõe a porta que a aplicação vai rodar
EXPOSE 8000

# Comando para rodar a aplicação com Uvicorn
# O host 0.0.0.0 é necessário para que a aplicação seja acessível de fora do contêiner
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
