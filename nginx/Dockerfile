# Estágio 1: Build do Frontend (se necessário, por exemplo, com Node.js)
# Neste caso, como são arquivos estáticos, podemos pular esta etapa.

# Estágio 2: Servidor Nginx
FROM nginx:1.25-alpine

# Copia os arquivos estáticos do frontend para o diretório padrão do Nginx
# O caminho é relativo ao contexto de build, que é a raiz do projeto.
COPY frontend/ /usr/share/nginx/html

# Copia o arquivo de configuração customizado do Nginx
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Expõe a porta 80
EXPOSE 80
