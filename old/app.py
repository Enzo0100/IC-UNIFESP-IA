import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Importações do LangChain e outras bibliotecas
from langchain_community.document_loaders import UnstructuredWordDocumentLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# --- CONFIGURAÇÃO E VARIÁVEIS GLOBAIS ---
load_dotenv()

# Para desenvolvimento, os IDs agora são caminhos para arquivos locais
GOOGLE_DOC_ID = "docs.docx"
GOOGLE_SHEET_ID = "planilha.xlsx"

# Pasta onde o banco de dados vetorial será salvo
VECTOR_STORE_PATH = "faiss_index"

# --- FUNÇÕES CORE (Lógica do RAG) ---

def carregar_e_vetorizar_documentos():
    """
    Função para carregar, dividir e vetorizar os documentos locais.
    Retorna um objeto de banco de dados vetorial (FAISS).
    """
    print("==> ETAPA 1: Carregamento e Vetorização <==")
    try:
        print("[1.1] Carregando documentos de fontes locais...")
        doc_loader = UnstructuredWordDocumentLoader(GOOGLE_DOC_ID)
        sheet_loader = UnstructuredExcelLoader(GOOGLE_SHEET_ID, mode="elements")
        
        docs = doc_loader.load()
        docs.extend(sheet_loader.load())

        if not docs:
            raise ValueError("Nenhum documento foi carregado. Verifique os nomes e os caminhos dos arquivos.")
        
        print(f"[1.2] Sucesso: {len(docs)} documentos carregados.")
        
        print("[1.3] Dividindo documentos em chunks...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        splits = text_splitter.split_documents(docs)
        print(f"[1.4] Sucesso: {len(splits)} chunks criados.")
        
        print("[1.5] Inicializando modelo de embedding do Google (Gemini)...")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        print("[1.6] Sucesso: Modelo de embedding do Google pronto para uso.")
        
        print("[1.7] Criando banco de dados vetorial FAISS a partir dos chunks...")
        vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
        print("[1.8] Sucesso: Banco de dados vetorial criado.")

        vectorstore.save_local(VECTOR_STORE_PATH)
        print(f"[1.9] Sucesso: Banco de dados vetorial salvo em '{VECTOR_STORE_PATH}'.")
        print("==> ETAPA 1 CONCLUÍDA <==")
        return vectorstore
    except Exception as e:
        print(f"!!! ERRO na ETAPA 1: {e}")
        raise

def inicializar_chatbot():
    """
    Carrega o banco de dados vetorial (ou o cria se não existir) e
    inicializa a cadeia de Pergunta e Resposta (RAG).
    """
    print("\n==> ETAPA 2: Inicialização do Chatbot <==")
    vectorstore = None
    if os.path.exists(VECTOR_STORE_PATH):
        try:
            print(f"[2.1] Encontrado banco de dados vetorial. Carregando de '{VECTOR_STORE_PATH}'...")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            vectorstore = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
            print("[2.2] Sucesso: Banco de dados vetorial carregado.")
        except Exception as e:
            print(f"!!! ERRO ao carregar o índice FAISS existente: {e}")
            print("!!! O índice pode estar corrompido ou incompatível. Recriando do zero...")
            vectorstore = carregar_e_vetorizar_documentos()
    else:
        print("[2.1] Nenhum banco de dados vetorial encontrado. Iniciando processo de criação...")
        vectorstore = carregar_e_vetorizar_documentos()

    print("[2.3] Inicializando o modelo LLM (Google Gemini)...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)
    print("[2.4] Sucesso: Modelo LLM carregado.")

    print("[2.5] Criando a cadeia de RAG com um retriever otimizado...")

    # Usando Maximal Marginal Relevance (MMR) para a busca.
    # Isso garante que os resultados sejam relevantes para a pergunta, mas também
    # diversificados, evitando trechos muito repetitivos ou redundantes.
    # 'k' é o número de documentos a serem retornados.
    # 'fetch_k' é o número de documentos a serem buscados inicialmente para o MMR reclassificar.
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={'k': 5, 'fetch_k': 20}
    )

    # O chain_type "stuff" é eficiente e funciona bem com modelos de grande contexto como o Gemini.
    # Ele "enfia" (stuffs) todos os trechos recuperados diretamente no prompt.

    # --- CRIAÇÃO DE PROMPT CUSTOMIZADO ---
    # Este prompt guia o LLM sobre como se comportar e como usar o contexto.
    prompt_template = """
    Você é um assistente especialista. Use os seguintes trechos de contexto para responder à pergunta do usuário.
    Se a resposta não estiver no contexto, diga que você não encontrou a informação nos documentos. Não tente inventar uma resposta.
    Seja claro e responda apenas com base nas informações dos documentos.

    Contexto:
    {context}

    Pergunta:
    {question}

    Resposta útil:
    """
    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT}
    )
    print("[2.6] Sucesso: Cadeia de RAG criada.")
    
    # Armazena a cadeia no cache global para reuso
    cache["qa_chain"] = qa_chain
    print("[2.7] Sucesso: Cadeia armazenada em cache.")
    print("==> ETAPA 2 CONCLUÍDA. API pronta para receber requisições. <==")

# --- GERENCIAMENTO DO CICLO DE VIDA DA API ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que roda na inicialização da API
    print("Iniciando a API...")
    inicializar_chatbot()
    yield
    # Código que roda no encerramento (limpeza)
    cache.clear()
    print("Cache limpo. API encerrada.")

# --- INICIALIZAÇÃO DA API FASTAPI ---

app = FastAPI(
    title="Chatbot RAG API",
    description="Uma API para fazer perguntas a documentos usando RAG e LLMs, com um frontend integrado.",
    version="1.1.0",
    lifespan=lifespan
)

# --- MIDDLEWARE (CORS) ---
# Permite que o frontend acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja para o seu domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE DADOS (Pydantic) ---

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    source_documents: list[dict]

# --- ENDPOINTS DA API ---

@app.get("/", tags=["Status"])
def read_root():
    """Endpoint de status para verificar se a API está no ar."""
    return {"status": "online", "message": "Bem-vindo à API do Chatbot RAG!"}

@app.post("/ask", response_model=QueryResponse, tags=["Chatbot"])
async def ask_question(request: QueryRequest):
    """
    Recebe uma pergunta e retorna a resposta baseada nos documentos.
    """
    if "qa_chain" not in cache:
        raise HTTPException(status_code=503, detail="Serviço indisponível. A cadeia de RAG não foi inicializada.")

    print(f"Recebida pergunta: {request.query}")
    
    try:
        # Invoca a cadeia com a pergunta
        response = cache["qa_chain"].invoke({"query": request.query})
        
        # Formata os documentos fonte para a resposta
        sources = [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in response["source_documents"]
        ]

        return QueryResponse(answer=response["result"], source_documents=sources)
    except Exception as e:
        print(f"Erro ao processar a pergunta: {e}")
        raise HTTPException(status_code=500, detail="Ocorreu um erro interno ao processar sua pergunta.")
    

@app.post("/ask", response_model=QueryResponse, tags=["Chatbot"])
async def ask_question(request: QueryRequest):
    """
    Recebe uma pergunta e retorna a resposta baseada nos documentos,
    exceto quando for small talk (sem consultar a base de dados).
    """
    # classifica antes de qualquer chamada ao RAG
    intent = classificar_intencao(request.query)

    if intent == "smalltalk":
        # resposta rápida sem tocar no vetor
        resposta = (
            "Oi! 👋\n"
            "Posso te ajudar a consultar os documentos quando quiser. "
            "Me pergunte algo como: “qual é o prazo do projeto?” ou “resuma a seção X do arquivo”."
        )
        return QueryResponse(answer=resposta, source_documents=[])

    # a partir daqui é pergunta de conteúdo -> usa RAG
    if "qa_chain" not in cache:
        raise HTTPException(status_code=503, detail="Serviço indisponível. A cadeia de RAG não foi inicializada.")

    print(f"Recebida pergunta: {request.query}")
    try:
        response = cache["qa_chain"].invoke({"query": request.query})
        sources = [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in response["source_documents"]
        ]
        return QueryResponse(answer=response["result"], source_documents=sources)
    except Exception as e:
        print(f"Erro ao processar a pergunta: {e}")
        raise HTTPException(status_code=500, detail="Ocorreu um erro interno ao processar sua pergunta.")


@app.post("/reindex", tags=["Administração"])
async def reindex_documents(background_tasks: BackgroundTasks):
    """
    Força a releitura e vetorização dos documentos do Google Drive em segundo plano.
    Use este endpoint se você atualizou os documentos fonte.
    """
    print("Requisição de reindexação recebida. O processo rodará em segundo plano.")
    background_tasks.add_task(inicializar_chatbot)
    return {
        "status": "success",
        "message": "A reindexação foi iniciada em segundo plano. A API continuará respondendo com a versão antiga dos dados até que o processo termine."
    }
