import psycopg2
from embed import Embedder
from settings import settings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LORE_DIR = BASE_DIR / 'app' / "lore"

lydia_file_path = LORE_DIR / "npc_lydia.md"
world_history_file_path = LORE_DIR / "world_history.md"
locations_file_path = LORE_DIR / "locations.md"

DB_CONFIG = {
    "host":     settings.db_host,
    "dbname":   settings.POSTGRES_DB,
    "user":     settings.POSTGRES_USER,
    "password": settings.POSTGRES_PASSWORD,
    "port":     settings.db_port,
}

def get_chunks(lydia_file_path):
    """Yields chunks of a file by a specified number of lines."""
    chunk, chunk_content, chunks = '', [], []
    with open(lydia_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            clean_line = line.strip()
            if not clean_line:
                continue  # Skip empty lines
            if clean_line.startswith('#') or clean_line.startswith('##'):
                if chunk:
                    chunks.append({chunk: ' '.join(chunk_content)})
                    chunk_content = []
                chunk = clean_line.lstrip("#- ").strip()
            else:
                chunk_content.append(clean_line)

    if chunk:  # Add the last chunk if it exists
        chunks.append({chunk: ' '.join(chunk_content)})               
    return chunks  
    
def process_all_files_in_directory(files: list[Path], cursor) -> list[dict]:
    section_title = []

    for file_path in files:
        file_name = file_path.name
        print(f"Processing file: {file_path}")
        chunks = get_chunks(file_path)
        npc_name = list(chunks[0].keys())[0] 

        for chunk in chunks:
            section_title = list(chunk.keys())[0] 

            if section_title == npc_name:
                continue # Skip the name of the npc 

            content = chunk[section_title]  # Get the content associated with the section title
            embed_text = f"{npc_name} - {section_title}: {content}"

            embedder = Embedder(embed_text)
            vector_embedding = embedder.get_embedding()

            cursor.execute("""              
            INSERT INTO lore_chunks (npc_name, source_file, section_title, content, embedding)
            VALUES (%s, %s, %s, %s, %s);
            """,(npc_name, file_name, section_title, content, vector_embedding))
                
        print(f"✓ Pipeline complete!")
   
if __name__ == "__main__":
    files = [lydia_file_path, world_history_file_path, locations_file_path]
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            process_all_files_in_directory(files, cursor)

    


        






