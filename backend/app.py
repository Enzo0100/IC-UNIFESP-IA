import os
from contextlib import asynccontextmanager
from typing import Dict, List, Literal, Optional, Tuple
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

# LangChain / LLM / Vector
from langchain_community.document_loaders import (
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# (Opcional) Busca na Web para o perfil "interesse_geral"
# Requer TAVILY_API_KEY no .env. Se não tiver, a API segue rodando só com RAG local.
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    TAVILY_AVAILABLE = True
except Exception:
    TAVILY_AVAILABLE = False

# =========================
# CONFIG & VARIÁVEIS GLOBAIS
# =========================
load_dotenv()

# Caminhos para os arquivos locais (como no seu exemplo)
GOOGLE_DOC_ID = "docs.docx"
GOOGLE_SHEET_ID = "planilha.xlsx"

# Pasta do índice FAISS
VECTOR_STORE_PATH = "faiss_index"

# Cache global de objetos para reuso
cache: Dict[str, object] = {}

# Perfis aceitos
Perfil = Literal["cidadao", "servidor_publico", "interesse_geral"]

# =========================
# FUNÇÕES CORE (RAG)
# =========================

def carregar_e_vetorizar_documentos() -> FAISS:
    print("==> ETAPA 1: Carregamento e Vetorização <==")
    try:
        print("[1.1] Carregando documentos locais...")
        doc_loader = UnstructuredWordDocumentLoader(GOOGLE_DOC_ID)
        sheet_loader = UnstructuredExcelLoader(GOOGLE_SHEET_ID, mode="elements")

        docs = doc_loader.load()
        docs.extend(sheet_loader.load())

        if not docs:
            raise ValueError("Nenhum documento foi carregado. Verifique os caminhos dos arquivos.")

        print(f"[1.2] Sucesso: {len(docs)} documentos carregados.")

        print("[1.3] Split em chunks...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        splits = text_splitter.split_documents(docs)
        print(f"[1.4] Sucesso: {len(splits)} chunks.")

        print("[1.5] Embeddings (Google)...")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        print("[1.6] Embeddings prontos.")

        print("[1.7] Construindo FAISS...")
        vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
        vectorstore.save_local(VECTOR_STORE_PATH)
        print(f"[1.8] Índice salvo em '{VECTOR_STORE_PATH}'.")
        print("==> ETAPA 1 CONCLUÍDA <==")
        return vectorstore
    except Exception as e:
        print(f"!!! ERRO ETAPA 1: {e}")
        raise

def carregar_vectorstore() -> FAISS:
    if os.path.exists(VECTOR_STORE_PATH):
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            return FAISS.load_local(
                VECTOR_STORE_PATH,
                embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as e:
            print(f"!!! ERRO ao carregar índice existente: {e}")
            print("Recriando índice do zero...")
            return carregar_e_vetorizar_documentos()
    else:
        return carregar_e_vetorizar_documentos()

def build_retriever(k: int = 5, fetch_k: int = 20):
    vectorstore = cache.get("vectorstore")
    if vectorstore is None:
        vectorstore = carregar_vectorstore()
        cache["vectorstore"] = vectorstore
    return vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": k, "fetch_k": fetch_k})


# ====== DETECÇÃO DE SMALL TALK + RESPOSTA VIA GEMINI ======

SMALL_TALK_PATTERNS = [
    r"^\s*oi\b", r"^\s*ol[áa]\b", r"^\s*e[ai]\b",
    r"\btudo bem\b", r"\btudo certo\b", r"\bbeleza\b|\bblz\b|\bsuave\b",
    r"\bopa\b|\bsalve\b", r"\bbom dia\b|\bboa tarde\b|\bboa noite\b",
    r"\bobrigad", r"\bvaleu\b", r"\btchau\b|\bat[eé] logo\b|\bat[eé]\b",
    r"\bcomo vai\b",
]

def is_small_talk(query: str) -> bool:
    q = (query or "").lower().strip()
    if len(q.split()) <= 5:
        import re
        for pat in SMALL_TALK_PATTERNS:
            if re.search(pat, q):
                return True
    return False

def responder_small_talk_gemini(query: str) -> str:
    """
    Usa o Gemini com um prompt básico para responder conversas gerais,
    sem consultar a base de dados.
    """
    llm = _get_llm(temp=0.7)  # mais criativo
    prompt_basico = f"""
Você é um assistente amigável e prestativo especializado em gestão e regimento territorial.
Sua missão é responder de forma breve, cordial e natural a interações casuais do usuário.

Pergunta ou cumprimento do usuário:
{query}

Resposta:
"""
    return llm.invoke(prompt_basico).content

# =========================
# NOVO: HEURÍSTICA — USAR OU NÃO O BANCO
# =========================
import re
from typing import cast

# limiar de similaridade do FAISS (nota: em FAISS do LangChain, score menor = mais similar)
FAISS_SCORE_THRESHOLD = 0.35  # ajuste fino depois com seus dados

_DOMINIO_KWS = [
    "parcelamento do solo", "loteamento", "desmembramento", "regularização fundiária",
    "fiscalização", "zoneamento", "outorga", "uso do solo", "iptu", "licenciamento",
    "auto de infração", "improbidade", "plano diretor", "lei complementar", "código urbanístico",
    "geoprocessamento", "croqui", "geo", "snirf", "sigef", "sei", "processo administrativo",
]

def _is_small_talk(q: str) -> bool:
    qn = (q or "").lower().strip()
    pats = [
        r"^\s*oi\b", r"^\s*ol[áa]\b", r"^\s*e[ai]\b", r"\bbom dia\b|\bboa tarde\b|\bboa noite\b",
        r"\btudo bem\b|\btudo certo\b|\bbeleza\b|\bblz\b|\bsuave\b",
        r"\bopa\b|\bsalve\b", r"\bobrigad", r"\bvaleu\b", r"\btchau\b|\bat[eé]( logo)?\b",
        r"\bcomo vai\b",
    ]
    if len(qn.split()) <= 5:
        return any(re.search(p, qn) for p in pats)
    return False

def should_use_database(query: str) -> bool:
    """
    Retorna True se parece consulta técnica que se beneficia do RAG; caso contrário False.
    Combina: (i) small talk; (ii) palavras do domínio; (iii) similaridade no FAISS.
    """
    q = (query or "").strip()
    if _is_small_talk(q):
        return False

    # heurística por palavras do domínio
    ql = q.lower()
    has_domain_kw = any(kw in ql for kw in _DOMINIO_KWS)

    # consulta rápida ao índice com score
    try:
        vectorstore = cache.get("vectorstore")
        if vectorstore is None:
            vectorstore = carregar_vectorstore()
            cache["vectorstore"] = vectorstore
        # retorna lista de (Document, score) com score menor = melhor
        scored = vectorstore.similarity_search_with_score(q, k=3)
        best_score = min((s for _, s in scored), default=1.0)
        # usa DB se há palavra de domínio OU se a similaridade foi boa o suficiente
        return has_domain_kw or (best_score <= FAISS_SCORE_THRESHOLD)
    except Exception as e:
        print(f"[Aviso] falha no teste de similaridade: {e}")
        # fallback: se contém kw do domínio, usa DB; senão, não usa
        return has_domain_kw

# =========================
# NOVO: AGENTE GENÉRICO (GEMINI) SEM RAG
# =========================
def responder_generico_gemini(query: str, history: List[Dict]) -> str:
    llm = _get_llm(temp=0.6)
    history_str = format_history(history)
    prompt = f"""
Você é um assistente amigável e claro, especializado em gestão/regimento territorial municipal no Brasil.
Objetivo: responder brevemente, de forma útil e sem citar documentos internos, a perguntas gerais ou conversas,
levando em conta o histórico da conversa para manter o contexto.

Histórico da conversa:
{history_str}

Nova pergunta do usuário:
{query}

Resposta breve e direta:
"""
    return llm.invoke(prompt).content

# =========================
# FUNÇÃO AUXILIAR DE HISTÓRICO
# =========================
def format_history(history: List[Dict]) -> str:
    """Formata o histórico para inclusão no prompt."""
    if not history:
        return "Nenhum histórico de conversa."
    return "\n".join([f"{'Usuário' if msg['role'] == 'user' else 'Assistente'}: {msg['content']}" for msg in history])


# =========================
# PROMPTS DOS AGENTES
# =========================
COORDENADOR_PROMPT = """
Você é um coordenador de estratégias de gestão territorial municipal.
Sua missão:
1) Identificar o problema principal.
2) Extrair 6–10 palavras-chave.
3) Escolher o agente: [1_juridico | 2_operacional | 3_dados_sistemas].
4) Dizer “precisa_consultar_base: sim|não” — só “sim” quando a resposta depender de detalhes documentais/legais específicos.
5) Justificar brevemente.

Se o tema for genérico/intro e não exigir citação, prefira “precisa_consultar_base: não”.
"""

AGENTE_JURIDICO_PROMPT = """
Você é o Agente 1_Jurídico (direito público/urbanístico/ambiental).
Sua resposta deve ser objetiva e com base na lei, usando o histórico e o contexto fornecidos.

Histórico da conversa:
{history}

Contexto para a nova pergunta (pode estar vazio):
{context}

Nova pergunta do usuário:
{question}

Resposta objetiva e fundamentada:
"""

AGENTE_OPERACIONAL_PROMPT = """
Você é o Agente 2_Operacional.
Sua resposta deve ser um passo a passo prático, considerando o histórico da conversa e o contexto.

Histórico da conversa:
{history}

Contexto para a nova pergunta (pode estar vazio):
{context}

Nova pergunta do usuário:
{question}

Resposta (passo a passo, sucinta, com modelo se couber):
"""

AGENTE_DADOS_PROMPT = """
Você é o Agente 3_Dados_e_Sistemas.
Sua resposta deve focar em fontes de dados, sistemas e validação, considerando o histórico e o contexto.

Histórico da conversa:
{history}

Contexto para a nova pergunta (pode estar vazio):
{context}

Nova pergunta do usuário:
{question}

Resposta (fontes/sistemas/consulta/validação):
"""


def montar_contexto_rag(query: str, perfil: Perfil, k: int = 6) -> Tuple[str, List[Dict]]:
    """
    Recupera contexto do FAISS e (se perfil == interesse_geral e Tavily disponível)
    agrega top resultados de web ao contexto.
    Retorna (contexto_textual, fontes).
    """
    retriever = build_retriever(k=k, fetch_k=max(20, k * 3))
    docs = retriever.invoke(query)


    fontes: List[Dict] = []
    partes = []

    for d in docs:
        partes.append(d.page_content)
        fontes.append({"tipo": "documento", "metadata": d.metadata})

    # Se for interesse_geral, tentar buscar web
    if perfil == "interesse_geral" and TAVILY_AVAILABLE and os.getenv("TAVILY_API_KEY"):
        try:
            tavily = TavilySearchResults(k=5)
            results = tavily.run(query)
            # results é str ou list dependendo da versão; tratamos genericamente:
            if isinstance(results, str):
                partes.append(f"\n[WEB] {results}")
                fontes.append({"tipo": "web", "metadata": {"fonte": "tavily", "conteudo": results}})
            elif isinstance(results, list):
                web_txt = []
                for r in results:
                    title = r.get("title") or ""
                    url = r.get("url") or ""
                    content = r.get("content") or ""
                    web_txt.append(f"Título: {title}\nURL: {url}\nConteúdo: {content}")
                    fontes.append({"tipo": "web", "metadata": {"title": title, "url": url}})
                partes.append("\n[WEB]\n" + "\n\n".join(web_txt))
        except Exception as e:
            print(f"[Aviso] Falha na busca web (Tavily): {e}")

    contexto = "\n\n---\n\n".join(partes) if partes else "Nenhum contexto encontrado."
    return contexto, fontes

# =========================
# AGENTE COORDENADOR & ESPECIALIZADOS
# =========================

def _get_llm(temp: float = 0.1):
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=temp)

def coordenar(query: str, perfil: Perfil) -> Dict:
    """
    Usa o RAG para montar contexto e o coordenador para classificar/rotear.
    """
    contexto, fontes = montar_contexto_rag(query, perfil, k=6)
    llm = _get_llm(0.2)

    prompt = PromptTemplate(
        template=COORDENADOR_RAG_PROMPT, input_variables=["context", "question"]
    )
    text = prompt.format(context=contexto, question=query)
    analise = llm.invoke(text).content

    # Heurística de fallback caso o modelo não estruture direito:
    agente = "2_operacional"
    analise_lower = (analise or "").lower()
    if "1_juridico" in analise_lower or "jurídico" in analise_lower or "juridico" in analise_lower:
        agente = "1_juridico"
    elif "3_dados_sistemas" in analise_lower or "dados" in analise_lower or "sistemas" in analise_lower:
        agente = "3_dados_sistemas"
    elif "2_operacional" in analise_lower or "operacional" in analise_lower or "modelo" in analise_lower:
        agente = "2_operacional"
    else:
        # Regras simples por palavras-chave, como backup
        kw = query.lower()
        if any(w in kw for w in ["lei", "jurisprud", "art.", "artigo", "sanção", "sanção", "crime", "improbidade", "competência", "competencia"]):
            agente = "1_juridico"
        elif any(w in kw for w in ["sistema", "base", "dados", "cnpj", "cpf", "geosampa", "sigef", "snci", "snirf", "sei", "sei!"]):
            agente = "3_dados_sistemas"
        else:
            agente = "2_operacional"

    return {
        "analise": analise,
        "agente_escolhido": agente,
        "contexto": contexto,
        "fontes": fontes,
    }

def responder_por_agente(agente: str, pergunta: str, contexto: str, history: List[Dict]) -> str:
    llm = _get_llm(0.0)
    history_str = format_history(history)
    input_vars = ["context", "question", "history"]

    if agente == "1_juridico":
        prompt = PromptTemplate(template=AGENTE_JURIDICO_PROMPT, input_variables=input_vars)
    elif agente == "3_dados_sistemas":
        prompt = PromptTemplate(template=AGENTE_DADOS_PROMPT, input_variables=input_vars)
    else:  # "2_operacional" default
        prompt = PromptTemplate(template=AGENTE_OPERACIONAL_PROMPT, input_variables=input_vars)

    text = prompt.format(context=contexto, question=pergunta, history=history_str)
    return llm.invoke(text).content

# =========================
# FASTAPI APP
# =========================

# Usando Redis para sessões
# (em prod, use Redis / banco e auth)
# SESSOES: Dict[str, Perfil] = {} # Removido, pois usaremos Redis

class StartRequest(BaseModel):
    session_id: str
    perfil: Perfil

class QueryRequest(BaseModel):
    session_id: Optional[str] = None
    query: str
    perfil: Optional[Perfil] = None  # fallback se não vier session_id

class QueryResponse(BaseModel):
    answer: str
    fonte_resumo: str
    agente_acionado: str
    source_documents: List[Dict]

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando a API...")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    print(f"FastAPI Cache inicializado com Redis em {redis_url}")
    inicializar_chatbot()
    yield
    cache.clear()
    print("Cache limpo. API encerrada.")

app = FastAPI(
    title="Chatbot RAG + Agentes (Gestão Territorial)",
    description="API com RAG, agentes coordenados e perfis (cidadão, servidor público, interesse geral).",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção: restrinja
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# INICIALIZAÇÃO CORE
# =========================

def inicializar_chatbot():
    print("\n==> ETAPA 2: Inicialização do Chatbot <==")
    # Garante vectorstore em cache
    cache["vectorstore"] = carregar_vectorstore()

    # Mantém também um QA "puro" disponível, caso queira usar em outros endpoints
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

# =========================
# ENDPOINTS
# =========================

@app.get("/", tags=["Status"])
def read_root():
    return {"status": "online", "message": "Bem-vindo à API do Chatbot RAG + Agentes!"}

@app.post("/start", tags=["Sessão"])
async def start_session(req: StartRequest):
    """
    Define o perfil do usuário no começo da interação.
    """
    if req.perfil not in ("cidadao", "servidor_publico", "interesse_geral"):
        raise HTTPException(status_code=400, detail="Perfil inválido.")
    
    # Armazenar perfil no Redis
    redis_client = FastAPICache.get_backend().redis
    await redis_client.set(f"session:{req.session_id}:perfil", req.perfil, ex=3600) # Expira em 1 hora
    
    return {"status": "ok", "session_id": req.session_id, "perfil": req.perfil}

# ====== AJUSTE NO ENDPOINT /ask ======
# =========================
# AJUSTE NO /ask — desvio condicional
# =========================
@app.post("/ask", response_model=QueryResponse, tags=["Chatbot"])
async def ask_question(request: QueryRequest):
    if "qa_chain" not in cache or "vectorstore" not in cache:
        raise HTTPException(status_code=503, detail="Serviço indisponível. RAG não inicializado.")

    # Perfil e Histórico da sessão
    perfil: Perfil
    chat_history: List[Dict] = []
    redis_client = FastAPICache.get_backend().redis

    if request.session_id:
        # Tenta obter perfil e histórico do Redis
        stored_perfil, stored_history = await redis_client.mget(
            f"session:{request.session_id}:perfil",
            f"session:{request.session_id}:history"
        )
        perfil = cast(Perfil, stored_perfil) if stored_perfil else (request.perfil or "interesse_geral")
        if stored_history:
            chat_history = json.loads(stored_history)
    else:
        perfil = request.perfil or "interesse_geral"

    print(f"[ASK] Session: {request.session_id} | Perfil: {perfil} | Pergunta: {request.query}")

    # 0) decidir se consulta o banco
    try:
        usa_db = should_use_database(request.query)
    except Exception as e:
        print(f"[Aviso] falha na decisão de uso do DB: {e}")
        usa_db = False  # fallback seguro

    resposta: str
    fonte_resumo: str
    agente_acionado: str
    source_documents: List[Dict] = []

    if not usa_db:
        # → resposta direta pelo agente genérico (Gemini) sem RAG
        resposta = responder_generico_gemini(request.query, chat_history)
        fonte_resumo = "Fluxo genérico (sem RAG): pergunta não exigia consulta ao banco."
        agente_acionado = "agente_generico_gemini"
    else:
        # 1) fluxo com coordenador + RAG
        try:
            diag = coordenar(request.query, perfil)
            agente_acionado = diag["agente_escolhido"]
            contexto = diag["contexto"]
            source_documents = diag["fontes"]
            fonte_resumo = diag["analise"]

            resposta = responder_por_agente(agente_acionado, request.query, contexto, chat_history)
        except Exception as e:
            print(f"Erro ao processar a pergunta com RAG: {e}")
            # fallback final: ainda assim tenta ajudar genericamente
            resposta = responder_generico_gemini(request.query, chat_history)
            fonte_resumo = "Falha no fluxo RAG; resposta genérica fornecida."
            agente_acionado = "fallback_generico_gemini"

    # Atualizar histórico no Redis se houver session_id
    if request.session_id:
        chat_history.append({"role": "user", "content": request.query})
        chat_history.append({"role": "assistant", "content": resposta})
        
        # Limita o histórico para não sobrecarregar
        MAX_HISTORY_LEN = 20  # 10 turnos
        if len(chat_history) > MAX_HISTORY_LEN:
            chat_history = chat_history[-MAX_HISTORY_LEN:]

        await redis_client.set(
            f"session:{request.session_id}:history",
            json.dumps(chat_history),
            ex=3600  # Expira em 1 hora
        )

    return QueryResponse(
        answer=resposta,
        fonte_resumo=fonte_resumo,
        agente_acionado=agente_acionado,
        source_documents=source_documents,
    )

@app.post("/reindex", tags=["Administração"])
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
