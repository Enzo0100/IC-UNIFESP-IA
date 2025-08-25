import re
from backend.utils.cache import cache
from backend.utils.vectorstore import carregar_vectorstore
from backend.utils.small_talk import is_small_talk as _is_small_talk
from backend.config import FAISS_SCORE_THRESHOLD, DOMINIO_KWS

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
    has_domain_kw = any(kw in ql for kw in DOMINIO_KWS)

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
