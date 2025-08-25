import os
import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

from backend.utils.cache import cache
from backend.utils.vectorstore import carregar_vectorstore, build_retriever
from backend.utils.agents import _get_llm

def inicializar_chatbot():
    """Função síncrona que carrega todos os modelos e dados."""
    print("\n==> ETAPA 2: Inicialização do Chatbot <==")
    try:
        # Garante vectorstore em cache
        cache["vectorstore"] = carregar_vectorstore()

        # Mantém também um QA "puro" disponível
        retriever = build_retriever()
        llm = _get_llm(0.0)

        base_prompt = PromptTemplate(
            template="""
            Você é um assistente especialista. Use os seguintes trechos de contexto para responder à pergunta do usuário.
            Se a resposta não estiver no contexto, diga que você não encontrou a informação nos documentos. Não tente inventar.
            
            Contexto:
            {context}

            Pergunta:
            {question}

            Resposta:
            """,
            input_variables=["context", "question"],
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": base_prompt},
        )
        cache["qa_chain"] = qa_chain

        print("==> ETAPA 2 CONCLUÍDA. API pronta. <==")
    except Exception as e:
        print(f"!!! ERRO FATAL durante a inicialização do chatbot: {e}")
        import traceback
        traceback.print_exc()


def inicializar_chatbot_thread_safe():
    """
    Wrapper para rodar a inicialização síncrona em um thread, garantindo
    que um loop de eventos asyncio esteja disponível para as bibliotecas que o exigem.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        inicializar_chatbot()
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando a API...")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
        await redis_client.ping()
        FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
        print(f"FastAPI Cache inicializado com Redis em {redis_url}")
    except Exception as e:
        print(f"!!! ERRO ao conectar com Redis em {redis_url}: {e}")
        print("!!! Cache não será utilizado.")

    # Carrega os dados e modelos em um thread de background para não travar a inicialização.
    # Usamos um thread padrão com um loop de eventos gerenciado manualmente para evitar
    # conflitos com bibliotecas que esperam um loop no contexto do thread.
    thread = threading.Thread(target=inicializar_chatbot_thread_safe, daemon=True)
    thread.start()
    
    yield
    
    cache.clear()
    print("Cache limpo. API encerrada.")
