import os
from typing import Dict, List, Tuple
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from backend.utils.vectorstore import build_retriever
from backend.models import Perfil

# Variável para checar disponibilidade da API Tavily
TAVILY_AVAILABLE = "TAVILY_API_KEY" in os.environ

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

COORDENADOR_RAG_PROMPT = """
Você é um coordenador de estratégias de gestão territorial municipal.
Sua missão:
1) Analisar o contexto e a pergunta.
2) Identificar o problema principal.
3) Extrair 6–10 palavras-chave relevantes da pergunta.
4) Escolher o agente mais adequado para responder: [1_juridico | 2_operacional | 3_dados_sistemas].
5) Justificar brevemente a escolha do agente.

Contexto dos documentos:
{context}

Pergunta do usuário:
{question}

Análise e Roteamento:
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

# =========================
# FUNÇÕES CORE DOS AGENTES
# =========================

def _get_llm(temp: float = 0.1):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY não encontrada no ambiente.")
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=temp, google_api_key=api_key)

def format_history(history: List[Dict]) -> str:
    """Formata o histórico para inclusão no prompt."""
    if not history:
        return "Nenhum histórico de conversa."
    return "\n".join([f"{'Usuário' if msg['role'] == 'user' else 'Assistente'}: {msg['content']}" for msg in history])

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
