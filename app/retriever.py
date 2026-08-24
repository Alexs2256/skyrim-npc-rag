import psycopg2
import embed as embed
import psycopg2.extras
from pathlib import Path
from settings import settings

DB_CONFIG = {
    "host":     settings.db_host,
    "dbname":   settings.POSTGRES_DB,
    "user":     settings.POSTGRES_USER,
    "password": settings.POSTGRES_PASSWORD,
    "port":     settings.db_port,
}

def get_query_embedding(text: str) -> list[float]:
    embed_text = f"User Prompt: {text}"
    embedder = embed.embed(embed_text)
    return embedder.get_embedding()

def retrieve_context(query: str, limit: int = 3) -> str:
    """
    Queries Postgres directly using raw SQL and the pgvector '<=>' operator.
    Returns a unified context string.
    """
    # Convert user query to vector
    query_vector = get_query_embedding(query)
    
    # Example format: '[0.123, -0.456, ...]'
    query_vector_str = str(query_vector)

    # Connect to PostgreSQL and execute vector search
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                     # Execute cosine distance similarity search
                     # '<=>' calculates cosine distance; ordering ASC yields closest matches first.
                    print(f"DEBUG: connecting to host={DB_CONFIG['host']} port={DB_CONFIG['port']} db={DB_CONFIG['dbname']}")
                    cursor.execute("SELECT COUNT(*) FROM lore_chunks;")
                    print(f"DEBUG: live row count = {cursor.fetchone()}")
                    cursor.execute(
                        """
                        SELECT npc_name, section_title, content, (1 - (embedding <=> %s::vector))  AS similarity
                        FROM lore_chunks
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                        """,
                        (query_vector_str, query_vector_str, limit)
                        )
                     
                    rows = cursor.fetchall()

                print(f"Raw rows returned: {len(rows)}")
                content_chunks=[]
                for row in rows:
                    embed_text = f"{row['npc_name']} - {row['section_title']}: {row['content']}"
                    content_chunks.append(embed_text)
                return content_chunks

    except Exception as e:
        print(f"Database retrieval failed: {e}")
        return ""

if __name__ == "__main__":
    queries = [
        "tell me about your weapons and combat style",
        "Lydia, tell me about your weapons and combat style",
    ]
    for round_num in range(3):
        for q in queries:
            context = retrieve_context(q)
            print(f"Round {round_num+1} | {len(context)} chars | {q!r}")
