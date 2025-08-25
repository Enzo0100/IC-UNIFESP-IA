import json
from typing import List, Dict, cast
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi_cache import FastAPICache

from backend.models import QueryRequest, QueryResponse, StartRequest, Perfil
from backend.utils.cache import cache
from backend.utils.heuristics import should_use_database
from backend.utils.agents import coordenar, responder_por_agente, responder_generico_gemini
from backend.api.lifespan import inicializar_chatbot

router = APIRouter()

@router.get("/", tags=["Status"])
def read_root():
    return {"status": "online", "message": "Bem-vindo à API IC Chatbot com RAG"}

@router.post("/start", tags=["Sessão"])
async def start_session(req: StartRequest):
    """
    Define o perfil do usuário no começo da interação.
    """
    if req.perfil not in ("cidadao", "servidor_publico", "interesse_geral"):
        raise HTTPException(status_code=400, detail="Perfil inválido.")
    
    try:
        redis_client = FastAPICache.get_backend().redis
        await redis_client.set(f"session:{req.session_id}:perfil", req.perfil, ex=3600) # Expira em 1 hora
    except AttributeError:
        # Redis não está disponível
        print(f"[Aviso] Redis não configurado. Perfil da sessão {req.session_id} não será salvo.")
        pass

    return {"status": "ok", "session_id": req.session_id, "perfil": req.perfil}

@router.post("/ask", response_model=QueryResponse, tags=["Chatbot"])
async def ask_question(request: QueryRequest):
    if "qa_chain" not in cache or "vectorstore" not in cache:
        raise HTTPException(status_code=503, detail="Serviço indisponível. RAG não inicializado.")

    perfil: Perfil
    chat_history: List[Dict] = []
    
    try:
        redis_client = FastAPICache.get_backend().redis
        if request.session_id:
            stored_perfil, stored_history = await redis_client.mget(
                f"session:{request.session_id}:perfil",
                f"session:{request.session_id}:history"
            )
            perfil = cast(Perfil, stored_perfil) if stored_perfil else (request.perfil or "interesse_geral")
            if stored_history:
                chat_history = json.loads(stored_history)
        else:
            perfil = request.perfil or "interesse_geral"
    except AttributeError:
        # Redis não está disponível
        perfil = request.perfil or "interesse_geral"
        print("[Aviso] Redis não configurado. Histórico e perfil não serão recuperados.")


    print(f"[ASK] Session: {request.session_id} | Perfil: {perfil} | Pergunta: {request.query}")

    try:
        usa_db = should_use_database(request.query)
    except Exception as e:
        print(f"[Aviso] falha na decisão de uso do DB: {e}")
        usa_db = False

    resposta: str
    fonte_resumo: str
    agente_acionado: str
    source_documents: List[Dict] = []

    if not usa_db:
        resposta = responder_generico_gemini(request.query, chat_history)
        fonte_resumo = "Fluxo genérico (sem RAG): pergunta não exigia consulta ao banco."
        agente_acionado = "agente_generico_gemini"
    else:
        try:
            diag = coordenar(request.query, perfil)
            agente_acionado = diag["agente_escolhido"]
            contexto = diag["contexto"]
            source_documents = diag["fontes"]
            fonte_resumo = diag["analise"]
            resposta = responder_por_agente(agente_acionado, request.query, contexto, chat_history)
        except Exception as e:
            print(f"Erro ao processar a pergunta com RAG: {e}")
            resposta = responder_generico_gemini(request.query, chat_history)
            fonte_resumo = "Falha no fluxo RAG; resposta genérica fornecida."
            agente_acionado = "fallback_generico_gemini"

    if request.session_id:
        chat_history.append({"role": "user", "content": request.query})
        chat_history.append({"role": "assistant", "content": resposta})
        
        MAX_HISTORY_LEN = 20
        if len(chat_history) > MAX_HISTORY_LEN:
            chat_history = chat_history[-MAX_HISTORY_LEN:]
        
        try:
            redis_client = FastAPICache.get_backend().redis
            await redis_client.set(
                f"session:{request.session_id}:history",
                json.dumps(chat_history),
                ex=3600
            )
        except AttributeError:
             print(f"[Aviso] Redis não configurado. Histórico da sessão {request.session_id} não será salvo.")
             pass


    return QueryResponse(
        answer=resposta,
        fonte_resumo=fonte_resumo,
        agente_acionado=agente_acionado,
        source_documents=source_documents,
    )

@router.post("/reindex", tags=["Administração"])
async def reindex_documents(background_tasks: BackgroundTasks):
    """
    Força releitura e vetorização dos documentos locais em background.
    """
    print("Requisição de reindexação recebida. Rodando em segundo plano...")
    background_tasks.add_task(inicializar_chatbot)
    return {
        "status": "success",
        "message": "Reindexação iniciada em background. A API segue respondendo com a versão anterior até concluir.",
    }
