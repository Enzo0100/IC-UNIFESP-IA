import os
from contextlib import asynccontextmanager
from typing import Dict, List, Literal, Optional, Tuple
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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
# PROMPTS
# =========================

COORDENADOR_PROMPT = """
Você é um agente coordenador de estratégias de gestão territorial em municípios brasileiros com vasta experiência na área pública, em especial no que tange ao parcelamento do solo, processos de urbanização, fiscalização territorial, regularização fundiária, planejamento urbano, ações civis públicas, interlocução institucional, governança territorial, processos administrativos, diagnósticos urbanos, relatórios, análises temporais e punições em caso de improbidade administrativa; com conhecimento também em legislação ambiental, administração pública, direito público e legislação urbanística.

Sua missão é:
1) Identificar o problema principal descrito (e.g., denúncia de loteamento clandestino, dúvida sobre competência institucional, pedido de modelo de notificação, enquadramento legal, exemplos de sucesso, dúvidas conceituais, sistemas/bases de dados públicos, etc.).
2) Extrair palavras-chave relevantes fornecidas pelo usuário.
3) Selecionar qual agente especializado deve responder:
   - Agente 1 — 1_juridico: dúvidas sobre legislação, jurisprudência, conceitos legais, marcos temporais, restrições legais, punições.
   - Agente 2 — 2_operacional: modelos de documentos, fluxos, checklists, procedimentos, respostas abrangentes e práticas.
   - Agente 3 — 3_dados_sistemas: sistemas e bases de dados públicas a consultar, fontes oficiais, como instruir coleta e validação de dados.

Regras:
- Responda de forma objetiva e clara.
- Se algo não estiver nos documentos/contexto, assuma papel orientador (diga o que falta e o que consultar).
- Para o perfil "interesse_geral", utilize também resultados de busca na internet quando indicado pelo tema.
"""

AGENTE_JURIDICO_PROMPT = """
Você é o Agente 1_Jurídico. Responda como especialista em direito público, legislação urbanística e ambiental,
com foco em parcelamento do solo, regularização fundiária, fiscalização e improbidade administrativa.
Use SOMENTE o contexto fornecido abaixo (documentos +, quando disponível, web) e seja preciso na fundamentação.
Se a informação não estiver disponível, aponte lacunas e indique normas/órgãos que usualmente cobrem o tema.

Contexto:
{context}

Pergunta do usuário:
{question}

Resposta (jurídico, objetiva, com referências normativas quando possível):
"""

AGENTE_OPERACIONAL_PROMPT = """
Você é o Agente 2_Operacional. Produza instruções práticas, modelos e checklists (quando pertinente),
incluindo campos, seções e itens obrigatórios. Aponte etapas, responsáveis possíveis e riscos.
Use SOMENTE o contexto fornecido abaixo (documentos +, quando disponível, web). Se faltar informação, diga o que coletar.

Contexto:
{context}

Pergunta do usuário:
{question}

Resposta (operacional, passo a passo, com modelo quando fizer sentido):
"""

AGENTE_DADOS_PROMPT = """
Você é o Agente 3_Dados_e_Sistemas. Indique bases e sistemas públicos relevantes (municipais, estaduais e federais),
campos/chaves de busca, como cruzar informações, critérios de qualidade e como registrar evidências.
Use SOMENTE o contexto fornecido abaixo (documentos +, quando disponível, web). Se faltar, recomende fontes confiáveis.

Contexto:
{context}

Pergunta do usuário:
{question}

Resposta (fontes, sistemas, como consultar, critérios de validação):
"""

# Prompt RAG "neutro" usado pelo coordenador para resumir/rotear (não devolvido ao usuário)
COORDENADOR_RAG_PROMPT = """
Atue como coordenador. Abaixo há contexto de documentos internos (e possivelmente web) + a pergunta do usuário.
Produza um pequeno diagnóstico com:
- Problema principal (1 linha);
- 6 a 10 palavras-chave;
- Agente recomendado: [1_juridico | 2_operacional | 3_dados_sistemas];
- Justificativa breve da escolha.

Contexto:
{context}

Pergunta:
{question}

Saída estruturada e concisa:
"""

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

def responder_por_agente(agente: str, pergunta: str, contexto: str) -> str:
    llm = _get_llm(0.0)

    if agente == "1_juridico":
        prompt = PromptTemplate(
            template=AGENTE_JURIDICO_PROMPT, input_variables=["context", "question"]
        )
    elif agente == "3_dados_sistemas":
        prompt = PromptTemplate(
            template=AGENTE_DADOS_PROMPT, input_variables=["context", "question"]
        )
    else:  # "2_operacional" default
        prompt = PromptTemplate(
            template=AGENTE_OPERACIONAL_PROMPT, input_variables=["context", "question"]
        )

    text = prompt.format(context=contexto, question=pergunta)
    return llm.invoke(text).content

# =========================
# FASTAPI APP
# =========================

# Estado de sessão simples em memória: session_id -> perfil
# (em prod, use Redis / banco e auth)
SESSOES: Dict[str, Perfil] = {}

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
def start_session(req: StartRequest):
    """
    Define o perfil do usuário no começo da interação.
    """
    if req.perfil not in ("cidadao", "servidor_publico", "interesse_geral"):
        raise HTTPException(status_code=400, detail="Perfil inválido.")
    SESSOES[req.session_id] = req.perfil
    return {"status": "ok", "session_id": req.session_id, "perfil": req.perfil}

@app.post("/ask", response_model=QueryResponse, tags=["Chatbot"])
async def ask_question(request: QueryRequest):
    """
    Recebe uma pergunta. Determina o perfil (da sessão ou do corpo) e executa:
    - Coordenador (diagnóstico + roteamento)
    - Agente especializado (jurídico / operacional / dados)
    - (Opcional) Busca web se perfil == interesse_geral
    """
    if "qa_chain" not in cache or "vectorstore" not in cache:
        raise HTTPException(status_code=503, detail="Serviço indisponível. RAG não inicializado.")

    # Descobre o perfil
    perfil: Optional[Perfil] = None
    if request.session_id and request.session_id in SESSOES:
        perfil = SESSOES[request.session_id]
    elif request.perfil:
        perfil = request.perfil
    else:
        # Default amigável: interesse_geral
        perfil = "interesse_geral"

    print(f"[ASK] Perfil: {perfil} | Pergunta: {request.query}")

    try:
        # 1) Coordenar (diagnóstico + rota)
        diag = coordenar(request.query, perfil)
        agente = diag["agente_escolhido"]
        contexto = diag["contexto"]
        fontes = diag["fontes"]
        analise = diag["analise"]

        # 2) Responder com o agente escolhido
        resposta = responder_por_agente(agente, request.query, contexto)

        # 3) Montar retorno
        return QueryResponse(
            answer=resposta,
            fonte_resumo=analise,
            agente_acionado=agente,
            source_documents=fontes,
        )
    except Exception as e:
        print(f"Erro ao processar a pergunta: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar sua pergunta.")

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
