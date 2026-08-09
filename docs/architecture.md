# Architecture

## High-level flow

```
Frontend (files/)
    │  user picks a file + types a topic
    ▼
POST /upload  (backend/app/api/upload.py)
    │
    ├─► validate extension + size          (backend/config.py)
    ├─► extract_text()                     (backend/services/parser.py)
    ├─► chunk_text()                       (backend/services/chunking.py)
    ├─► embed_texts()                      (backend/services/embeddings.py)
    └─► ensure_collection() + store_embeddings()
                                            (backend/services/qdrant_service.py)
    │
    ▼
returns { document_id, filename, characters, total_chunks }
    │
    ▼
POST /study-plan  (backend/api/study_plan.py)
    │
    ├─► retrieve_relevant_chunks(topic, document_id)
    │       embed_query()                  (backend/services/embeddings.py)
    │       Qdrant search, filtered by document_id
    │                                       (backend/services/retrieval.py)
    ├─► build_context_string()             (backend/services/retrieval.py)
    └─► generate_study_plan(topic, context) (backend/services/llm_service.py → Groq)
    │
    ▼
returns { topic, summary, estimated_total_hours, days[], retrieval{ chunks_retrieved, sources[] } }
    │
    ▼
result.html renders the real response (files/script.js)
```

## Components

| Layer | File(s) | Responsibility |
|---|---|---|
| Frontend | `files/*.html`, `files/script.js`, `files/config.js` | Static UI. `script.js` calls the backend directly with `fetch()` — no simulated/fake pipeline. `config.js` holds `API_BASE_URL`, the one place to change for deployment. |
| Config | `backend/config.py` | Single source of truth for all settings: Groq key, Qdrant connection, upload limits, chunk size, CORS origins. Everything else imports `settings` from here. |
| Upload API | `backend/app/api/upload.py` | Validates the file, then runs it through parse → chunk → embed → store. Returns a `document_id`, not raw chunks. |
| Parsing | `backend/services/parser.py` | Extracts plain text from PDF (`pypdf`), TXT, or DOCX (`python-docx`). |
| Chunking | `backend/services/chunking.py` | Splits text into overlapping fixed-size chunks (`List[str]`), so no sentence is lost at a hard boundary. |
| Embeddings | `backend/services/embeddings.py` | Local `sentence-transformers` model (`all-MiniLM-L6-v2`, 384-dim). No API key or network call needed at inference time. |
| Vector storage | `backend/services/qdrant_service.py` | Owns the Qdrant client, collection creation, and upserts. Each point's payload carries `document_id`, `filename`, `chunk_index`, and the chunk text. |
| Retrieval | `backend/services/retrieval.py` | Embeds the query topic and searches Qdrant, filtered by `document_id` when provided — this is what keeps one upload's results from leaking into another's. |
| Study plan API | `backend/api/study_plan.py` | Ties retrieval + LLM together. Adds real `retrieval.chunks_retrieved` / `retrieval.sources` metadata to the response — never a fabricated score. |
| LLM | `backend/services/llm_service.py` | Calls Groq (`llama-3.3-70b-versatile`) with the retrieved context, forces JSON output, validates the shape before returning it. |
| App entrypoint | `backend/app/main.py` | Wires both routers together, adds CORS middleware for local frontend dev. |

## Data isolation

Every upload gets a UUID `document_id`. `/study-plan` accepts that ID and filters the Qdrant search to only chunks with a matching `document_id` in their payload — so a query about one uploaded file won't pull in unrelated chunks from a different upload sitting in the same collection.

This is **document-level** isolation, not full multi-user session/auth isolation — there's no login system, so anyone with a `document_id` (returned directly in the `/upload` response) can query that document. That's an accepted limitation for an MVP/fellowship project; see `docs/setup.md` and the README for the honest caveat.

## Why Groq instead of Gemini

The original design called for Gemini, but the API key available for this deployment is a Groq key, so `llm_service.py` uses the `groq` Python SDK's chat completions endpoint with `response_format={"type": "json_object"}` instead of the `google-genai` SDK. The prompt, schema, and "grounded only in retrieved context" behavior are unchanged — only the client and model name differ.
