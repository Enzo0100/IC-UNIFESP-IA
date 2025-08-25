import os
from langchain_community.document_loaders import (UnstructuredWordDocumentLoader, UnstructuredExcelLoader)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from backend.utils.cache import cache
from backend.config import GOOGLE_DOC_ID, GOOGLE_SHEET_ID, VECTOR_STORE_PATH

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
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY não encontrada no ambiente.")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
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
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY não encontrada no ambiente.")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
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
