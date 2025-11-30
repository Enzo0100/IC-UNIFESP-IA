# Chatbot RAG API com FastAPI e LangChain

Esta é uma API construída com FastAPI que implementa um chatbot de Geração Aumentada por Recuperação (RAG). O chatbot utiliza documentos locais (Word e Excel) como base de conhecimento para responder a perguntas. O frontend é uma aplicação de página única (SPA) servida diretamente pela API.

## Arquitetura

### Atualização (Otimização com LangGraph)

Foi adicionada uma pipeline baseada em LangGraph (`backend/utils/langgraph_pipeline.py`) que decide dinamicamente o fluxo:
- Small talk (1 chamada LLM, sem retrieval)
- Pergunta genérica (1 chamada LLM)
- Fluxo RAG completo (retrieval + coordenação + resposta com agente)

Benefícios:
- Menos chamadas redundantes (coordenação e resposta compartilham o mesmo contexto recuperado).
- Cache de retrievers por parâmetros (k/fetch_k) evitando recriação.
- Early exit rápido para perguntas simples, reduzindo latência percebida (objetivo: cair de ~50s para poucos segundos em cenários simples).

Fallback: se ocorrer erro no grafo, o endpoint retorna ao fluxo genérico anterior automaticamente.

O projeto é composto por um backend (API) e um frontend (interface do usuário).

- **Backend (FastAPI)**:
  - Gerencia a lógica de RAG usando a biblioteca LangChain.
  - Carrega documentos (`.docx`, `.xlsx`), os divide em trechos (chunks) e os vetoriza usando embeddings do Google (Gemini).
  - Armazena os vetores em um banco de dados local [FAISS](https://github.com/facebookresearch/faiss) para buscas rápidas de similaridade.
  - Expõe endpoints para receber perguntas, realizar buscas nos documentos e retornar respostas geradas por um Modelo de Linguagem Grande (LLM), também do Google (Gemini).
  - Serve os arquivos estáticos do frontend.

- **Frontend (HTML, CSS, JavaScript)**:
  - Uma interface simples para que o usuário possa enviar perguntas à API e visualizar as respostas.
  - Comunica-se com o endpoint `/ask` do backend.

## Como Funciona (Fluxo do RAG)

1.  **Inicialização**:
    - Ao iniciar, a API verifica a existência de um banco de dados vetorial (índice FAISS) na pasta `faiss_index`.
    - Se o índice não existir, a API executa o processo de **indexação**:
        - Carrega os arquivos `docs.docx` e `planilha.xlsx`.
        - Divide o conteúdo dos documentos em pequenos trechos (chunks).
        - Converte cada trecho em um vetor numérico (embedding) usando o modelo `models/embedding-001` do Google.
        - Salva esses vetores em um índice FAISS local.
    - Se o índice já existir, ele é carregado diretamente na memória.
    - Por fim, a cadeia de Pergunta e Resposta (`RetrievalQA`) é inicializada com o LLM `gemini-pro` e um prompt customizado que instrui o modelo a responder com base apenas nos documentos fornecidos.

2.  **Recebendo uma Pergunta (`/ask`)**:
    - O usuário envia uma pergunta através do frontend.
    - A API recebe a pergunta no endpoint `/ask`.
    - A pergunta do usuário é convertida em um vetor (embedding).
    - O FAISS é usado para buscar os trechos de texto dos documentos cujos vetores são mais similares ao vetor da pergunta (busca de similaridade).
    - Os trechos recuperados (contexto) e a pergunta original são enviados ao LLM (Gemini) através de um prompt estruturado.
    - O LLM gera uma resposta com base no contexto fornecido.
    - A API retorna a resposta e os trechos de fonte para o frontend.

## Endpoints da API

A API expõe os seguintes endpoints:

- `GET /`
  - **Descrição**: Endpoint de status para verificar se a API está online.
  - **Resposta**:
    ```json
    {
      "status": "online",
      "message": "Bem-vindo à API do Chatbot RAG!"
    }
    ```

- `POST /ask`
  - **Descrição**: Recebe uma pergunta e retorna a resposta gerada pelo RAG.
  - **Corpo da Requisição**:
    ```json
    {
      "query": "Qual é a sua pergunta?"
    }
    ```
  - **Resposta de Sucesso**:
    ```json
    {
      "answer": "A resposta gerada pelo modelo.",
      "source_documents": [
        {
          "content": "O trecho do documento usado como fonte.",
          "metadata": { "source": "docs.docx", ... }
        }
      ]
    }
    ```

- `POST /reindex`
  - **Descrição**: Dispara a reindexação dos documentos em segundo plano. Útil quando os arquivos `docs.docx` ou `planilha.xlsx` são atualizados. A API continuará funcionando com os dados antigos até que a nova indexação seja concluída.
  - **Resposta**:
    ```json
    {
      "status": "success",
      "message": "A reindexação foi iniciada em segundo plano..."
    }
    ```

## Como Executar o Projeto

### Pré-requisitos

- Python 3.9+
- Uma chave de API do Google AI Studio.

### Instalação

1.  **Clone o repositório:**
    ```bash
    git clone <URL_DO_REPOSITORIO>
    cd <NOME_DA_PASTA>
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    - Renomeie o arquivo `.env.example` para `.env`.
    - Abra o arquivo `.env` e adicione sua chave da API do Google:
      ```
      GOOGLE_API_KEY="SUA_CHAVE_API_AQUI"
      ```

### Execução

1.  **Inicie a API:**
    ```bash
    uvicorn app:app --reload
    ```
    A API estará disponível em `http://127.0.0.1:8000`.

2.  **Acesse o Frontend:**
    - Abra seu navegador e acesse `http://127.0.0.1:8000`.
    - A interface do chatbot será carregada, e você poderá começar a fazer perguntas.

3.  **Documentação Interativa da API:**
    - Para ver a documentação interativa gerada pelo FastAPI (Swagger UI), acesse `http://127.0.0.1:8000/docs`.

## Docker

O projeto também pode ser executado com Docker e Docker Compose.

### Estrutura esperada de build

O `Dockerfile` está em `docker/Dockerfile`, mas ele referencia arquivos usando caminhos relativos à RAIZ do repositório (contexto de build). Por isso, ao executar o build você deve estar na raiz do projeto e apontar o Dockerfile explicitamente.

Principais instruções do Dockerfile:
- `COPY docker/requirements.txt .` -> copia `docker/requirements.txt` para `/app/requirements.txt` dentro da imagem.
- `COPY backend/ ./backend/` -> copia o diretório `backend`.
- `COPY base_de_dados/ ./base_de_dados/` -> copia documentos de origem (necessários para indexação inicial se você quiser gerar o índice dentro do container).

Se você executar `docker build` dentro da pasta `docker/`, o caminho relativo `docker/requirements.txt` não existirá dentro desse contexto, causando o erro: `failed to calculate checksum ... "/docker/requirements.txt": not found`.

### Build simples
```bash
docker build -f docker/Dockerfile -t chatbot-rag:latest .
```

### Executar container
```bash
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY="SUA_CHAVE" chatbot-rag:latest
```
A API ficará disponível em `http://localhost:8000`.

### Docker Compose
Na raiz do repo:
```bash
docker-compose -f docker/docker-compose.yml up --build
```

### Dicas
- Se não quiser copiar os arquivos de documentos ou índice FAISS para a imagem (para mantê-la leve), remova ou ajuste as instruções `COPY base_de_dados/` e ignore `faiss_index/` (já está no `.dockerignore` da raiz).
- Para montar documentos dinamicamente:
```bash
docker run --rm -p 8000:8000 -v $(pwd)/base_de_dados:/app/base_de_dados -v $(pwd)/faiss_index:/app/faiss_index -e GOOGLE_API_KEY="SUA_CHAVE" chatbot-rag:latest
```


deep learning libs > langchain libs > lang graph > backend fastapi > docker    