# Estágio 1: Instalar dependências
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
RUN npx update-browserslist-db@latest

# Estágio 2: Aplicação de desenvolvimento
FROM node:20-alpine
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Expõe a porta que o Vite usa
EXPOSE 8080

# Comando para iniciar o servidor de desenvolvimento do Vite
CMD ["npm", "run", "dev"]
