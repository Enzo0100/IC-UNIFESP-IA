# Estágio 1: Base com Python
FROM python:3.10-slim

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Adiciona o diretório de trabalho ao PYTHONPATH para garantir que os módulos sejam encontrados
ENV PYTHONPATH=/app

# Copia o arquivo de dependências. O contexto de build deve ser a raiz do projeto.
COPY docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos do projeto para o WORKDIR
COPY . .

# Expõe a porta que a aplicação vai rodar
EXPOSE 8000

# Comando para rodar a aplicação com Uvicorn, apontando para o local correto do app
# O host 0.0.0.0 é necessário para que a aplicação seja acessível de fora do contêiner
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
