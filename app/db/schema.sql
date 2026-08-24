-- Enable the pgvector extension (adds the VECTOR data type + similarity search operators)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- Table 1: lore_chunks
-- Stores every chunked piece of your .md lore files as a vector
-- ============================================================
CREATE TABLE IF NOT EXISTS lore_chunks (
    id           SERIAL PRIMARY KEY,
    npc_name     TEXT NOT NULL,       -- e.g. "Lydia"
    source_file   TEXT NOT NULL,       -- e.g. "npc_lydia.md"
    section_title TEXT,                -- e.g. "Backstory" (the ## heading it came from)
    content       TEXT NOT NULL,       -- the actual chunk text
    embedding     VECTOR(1536),         -- Gemini text-embedding-004 outputs 768-dim vectors
    created_at    TIMESTAMP DEFAULT NOW()
);

-- -- Index for fast similarity search (cosine distance is standard for text embeddings)
-- CREATE INDEX IF NOT EXISTS lore_chunks_embedding_idx
--     ON lore_chunks
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- ============================================================
-- Table 2: game_state
-- Direct-lookup (non-vector) facts: quests, reputation, inventory
-- One row per session/player
-- ============================================================
CREATE TABLE IF NOT EXISTS game_state (
    session_id      TEXT PRIMARY KEY,
    npc_name        TEXT NOT NULL,
    reputation      INTEGER DEFAULT 5,     -- 0-10 scale
    active_quest    TEXT,
    completed_quests TEXT[],               -- array of quest names already done
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- Table 3: conversation_history
-- Short-term memory: recent exchanges per session
-- ============================================================
CREATE TABLE IF NOT EXISTS conversation_history (
    id          SERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,       -- 'player' or 'npc'
    message     TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);
