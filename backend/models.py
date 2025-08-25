from pydantic import BaseModel
from typing import List, Optional, Dict, Literal

# Perfis aceitos
Perfil = Literal["cidadao", "servidor_publico", "interesse_geral"]

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
