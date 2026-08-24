# Skyrim NPC RAG Chatbot — Setup Log

## Step 1: Start the database

From the project root, run:

```bash
docker compose up -d
```

This will:
1. Pull the `ankane/pgvector` image (Postgres + pgvector extension already installed)
2. Start a container named `npc_rag_db` on port 5432
3. Automatically run `app/db/schema.sql` the FIRST time it creates the database,
   which creates your three tables: `lore_chunks`, `game_state`, `conversation_history`

## Step 2: Verify it worked

Check the container is running:
```bash
docker ps
```
You should see `npc_rag_db` listed.

Connect to the database directly to confirm the tables exist:
```bash
docker exec -it npc_rag_db psql -U npc_admin -d npc_rag -c "\dt"
```
You should see all 3 tables listed: `lore_chunks`, `game_state`, `conversation_history`.

Confirm the vector extension is active:
```bash
docker exec -it npc_rag_db psql -U npc_admin -d npc_rag -c "\dx"
```
You should see `vector` in the extension list.

## Troubleshooting

- **Port 5432 already in use** → you likely have Postgres running locally already.
  Either stop it, or change the port mapping in `docker-compose.yml` to `"5433:5432"`.
- **Permission denied on schema.sql** → make sure the file exists at
  `app/db/schema.sql` relative to where you run `docker compose up`.
- **Tables don't appear** → the init script only runs the FIRST time the volume is created.
  If you already started the container once before adding schema.sql, wipe it and restart:
  ```bash
  docker compose down -v
  docker compose up -d
  ```

## Next step
Once tables are confirmed, we move to writing your first lore `.md` file
and the ingestion pipeline (chunker → embedder → load into `lore_chunks`).
