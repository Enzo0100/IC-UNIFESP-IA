from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.api.lifespan import lifespan
from backend.api.endpoints import router as api_router

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="Chatbot RAG + Agentes (Gestão Territorial)",
    description="API com RAG, agentes coordenados e perfis (cidadão, servidor público, interesse geral).",
    version="2.0.0",
    lifespan=lifespan,
)

# Adiciona o middleware CORS para permitir requisições de qualquer origem
# Em um ambiente de produção, é recomendado restringir as origens permitidas
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui o roteador com todos os endpoints da API
app.include_router(api_router, prefix="/api")

# Ponto de entrada para execução com uvicorn (opcional, para desenvolvimento)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
