"""Pipeline RAG usando LangGraph

Objetivos de performance:
- Reduzir chamadas redundantes ao LLM (coordenação + resposta) mantendo lógica atual.
- Early exit para small talk (1 chamada LLM) ou perguntas genéricas (1 chamada LLM).
- Só executar retrieval + coordenação + resposta quando heurística indicar necessidade de base.
- Compartilhar contexto recuperado entre coordenador e agente para evitar re-retrieval.

Nós do grafo:
1) decide -> retorna estado {'flow': 'small_talk'|'generico'|'rag'}
2) retrieve_and_route (se flow == 'rag'): faz retrieval, coordena e decide agente
3) answer: gera resposta final (usa small_talk / generico / agente específico)

Saída final padronizada: {
  'answer': str,
  'fonte_resumo': str,
  'agente_acionado': str,
  'source_documents': List[dict]
}
"""
from typing import Dict, Any, List
import time
import logging
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from backend.utils.small_talk import is_small_talk, responder_small_talk_gemini
from backend.utils.heuristics import should_use_database
from backend.utils.agents import coordenar, responder_por_agente, responder_generico_gemini
from backend.models import Perfil

# Estado compartilhado do grafo
class ChatState(BaseModel):
    query: str
    perfil: Perfil
    history: List[Dict] = Field(default_factory=list)
    flow: str | None = None
    # Campos preenchidos em fluxo RAG
    contexto: str | None = None
    fontes: List[Dict] = Field(default_factory=list)
    analise: str | None = None
    agente: str | None = None
    # Resultado final
    answer: str | None = None
    fonte_resumo: str | None = None
    agente_acionado: str | None = None
    source_documents: List[Dict] = Field(default_factory=list)


# ---------- NÓS ----------

logger = logging.getLogger(__name__)


def decide(state: ChatState) -> ChatState:
    q = state.query
    # 1) Small talk
    if is_small_talk(q):
        state.flow = 'small_talk'
        logger.debug({
            'event': 'decide',
            'flow': state.flow,
            'query': q[:120]
        })
        return state
    # 2) Heurística para RAG
    try:
        usar = should_use_database(q)
    except Exception:
        usar = False
    state.flow = 'rag' if usar else 'generico'
    logger.debug({
        'event': 'decide',
        'flow': state.flow,
        'usar_db': usar,
        'query': q[:120]
    })
    return state


def retrieve_and_route(state: ChatState) -> ChatState:
    t0 = time.time()
    diag = coordenar(state.query, state.perfil)
    state.contexto = diag['contexto']
    state.fontes = diag['fontes']
    state.analise = diag['analise']
    state.agente = diag['agente_escolhido']
    logger.debug({
        'event': 'retrieve_and_route',
        'agente': state.agente,
        'n_fontes': len(state.fontes),
        'dur_ms': round((time.time() - t0) * 1000, 1)
    })
    return state


def answer(state: ChatState) -> ChatState:
    if state.flow == 'small_talk':
        ans = responder_small_talk_gemini(state.query)
        state.answer = ans
        state.fonte_resumo = 'Small talk: resposta direta sem RAG.'
        state.agente_acionado = 'small_talk'
        state.source_documents = []
        logger.debug({'event': 'answer', 'flow': 'small_talk'})
        return state
    if state.flow == 'generico':
        ans = responder_generico_gemini(state.query, state.history)
        state.answer = ans
        state.fonte_resumo = 'Fluxo genérico: heurística indicou que não era necessário RAG.'
        state.agente_acionado = 'agente_generico_gemini'
        state.source_documents = []
        logger.debug({'event': 'answer', 'flow': 'generico'})
        return state
    # fluxo RAG
    ans = responder_por_agente(state.agente or '2_operacional', state.query, state.contexto or '', state.history)
    state.answer = ans
    state.fonte_resumo = state.analise or 'Análise não retornada.'
    state.agente_acionado = state.agente or '2_operacional'
    state.source_documents = state.fontes
    logger.debug({'event': 'answer', 'flow': 'rag', 'agente': state.agente_acionado, 'n_docs': len(state.source_documents)})
    return state


# ---------- BUILD GRAPH ----------

def build_chat_graph():
    graph = StateGraph(ChatState)
    graph.add_node('decide', decide)
    graph.add_node('retrieve_and_route', retrieve_and_route)
    graph.add_node('answer', answer)

    graph.add_edge(START, 'decide')
    # Condicional: se flow == rag -> retrieve_and_route -> answer, senão, decide -> answer
    def cond_route(state: ChatState):  # retorna próximo nó
        return 'retrieve_and_route' if state.flow == 'rag' else 'answer'

    graph.add_conditional_edges('decide', cond_route, {'retrieve_and_route': 'retrieve_and_route', 'answer': 'answer'})
    graph.add_edge('retrieve_and_route', 'answer')
    graph.add_edge('answer', END)
    return graph.compile()

# Singleton / cache local
_graph_instance = None

def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_chat_graph()
    return _graph_instance


def run_graph_query(query: str, perfil: Perfil, history: List[Dict]) -> Dict[str, Any]:
    t0 = time.time()
    graph = get_graph()
    init = ChatState(query=query, perfil=perfil, history=history)
    try:
        raw_state = graph.invoke(init)  # Pode retornar ChatState ou dict dependendo da versão do LangGraph
    except Exception as e:
        logger.error({'event': 'graph_invoke_error', 'error': str(e)})
        raise

    tipo = type(raw_state).__name__

    # Normaliza para ChatState se vier dict
    if isinstance(raw_state, ChatState):
        final_state = raw_state
    elif isinstance(raw_state, dict):
        try:
            final_state = ChatState(**raw_state)
        except Exception as e:
            logger.warning({'event': 'state_normalization_failed', 'tipo': tipo, 'error': str(e)})
            dur = round((time.time() - t0) * 1000, 1)
            logger.debug({'event': 'run_graph_query_end', 'tipo_estado': tipo, 'dur_ms': dur})
            return {
                'answer': raw_state.get('answer', ''),
                'fonte_resumo': raw_state.get('fonte_resumo', ''),
                'agente_acionado': raw_state.get('agente_acionado', ''),
                'source_documents': raw_state.get('source_documents', []),
            }
    else:
        logger.warning({'event': 'unexpected_state_type', 'tipo': tipo})
        dur = round((time.time() - t0) * 1000, 1)
        logger.debug({'event': 'run_graph_query_end', 'tipo_estado': tipo, 'dur_ms': dur})
        return {
            'answer': '',
            'fonte_resumo': 'Tipo de estado final inesperado',
            'agente_acionado': '',
            'source_documents': [],
        }

    dur = round((time.time() - t0) * 1000, 1)
    logger.debug({'event': 'run_graph_query_end', 'tipo_estado': tipo, 'dur_ms': dur, 'flow': final_state.flow})

    return {
        'answer': final_state.answer or '',
        'fonte_resumo': final_state.fonte_resumo or '',
        'agente_acionado': final_state.agente_acionado or '',
        'source_documents': final_state.source_documents,
    }
