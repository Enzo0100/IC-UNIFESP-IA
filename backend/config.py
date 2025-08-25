# =========================
# CONFIG & VARIÁVEIS GLOBAIS
# =========================

# Caminhos para os arquivos locais (relativos à raiz do projeto)
GOOGLE_DOC_ID = "base_de_dados/docs.docx"
GOOGLE_SHEET_ID = "base_de_dados/planilha.xlsx"

# Pasta do índice FAISS
VECTOR_STORE_PATH = "faiss_index"

# Padrões para detecção de Small Talk
SMALL_TALK_PATTERNS = [
    r"^\s*oi\b", r"^\s*ol[áa]\b", r"^\s*e[ai]\b",
    r"\btudo bem\b", r"\btudo certo\b", r"\bbeleza\b|\bblz\b|\bsuave\b",
    r"\bopa\b|\bsalve\b", r"\bbom dia\b|\bboa tarde\b|\bboa noite\b",
    r"\bobrigad", r"\bvaleu\b", r"\btchau\b|\bat[eé] logo\b|\bat[eé]\b",
    r"\bcomo vai\b",
]

# Limiar de similaridade do FAISS para a heurística
FAISS_SCORE_THRESHOLD = 0.35

# Palavras-chave de domínio para a heurística
DOMINIO_KWS = [
    "parcelamento do solo", "loteamento", "desmembramento", "regularização fundiária",
    "fiscalização", "zoneamento", "outorga", "uso do solo", "iptu", "licenciamento",
    "auto de infração", "improbidade", "plano diretor", "lei complementar", "código urbanístico",
    "geoprocessamento", "croqui", "geo", "snirf", "sigef", "sei", "processo administrativo",
]
