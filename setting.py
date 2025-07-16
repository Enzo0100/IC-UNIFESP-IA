if dev

else:
    from dotenv import load_dotenv
    load_dotenv()
    qdrant.start
    
redis = redis.Redis(host='localhost', port=6379, db=0)


postgres = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT")
)

criar tabela conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


Usar webtool para que o LLM tenha acesso a internet e possa buscar informações atualizadas.