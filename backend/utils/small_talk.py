import re
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import SMALL_TALK_PATTERNS

import os

def _get_llm(temp: float = 0.1):
    # Esta função é duplicada em agents.py, idealmente seria centralizada
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY não encontrada no ambiente.")
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=temp, google_api_key=api_key)

def is_small_talk(query: str) -> bool:
    q = (query or "").lower().strip()
    if len(q.split()) <= 5:
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
