# 📚 AI Study Companion

An AI-powered Study Companion that lets a student upload notes/syllabus
(PDF, TXT, or DOCX), name a topic, and get back a day-by-day study plan
generated with Retrieval-Augmented Generation (RAG) — grounded only in
what's actually in the uploaded document.

---

## 🚀 Features

- Upload PDF, TXT, or DOCX notes (10MB limit)
- Document parsing → chunking → embedding → Qdrant vector storage
- Semantic retrieval scoped to the document you just uploaded
- AI study-plan generation (Groq) grounded in retrieved context only
- Static HTML/CSS/JS frontend that calls the real backend (no simulated pipeline)

---

## 🛠 Tech Stack

- **Frontend:** static HTML/CSS/vanilla JS (`files/`)
- **Backend:** FastAPI (`backend/`)
- **Embeddings:** sentence-transformers (`all-MiniLM-L6-v2`, 384-dim), local, no API key needed
- **Vector DB:** Qdrant
- **LLM:** Groq (`llama-3.3-70b-versatile`) — swapped in place of Gemini, since that's the API key available for this deployment
- **Parsing:** pypdf, python-docx

---

AI-Study-Companion/
│
├── .env
├── .env.example
├── LICENSE
├── pytest.ini
├── README.md
├── test_pipeline.py
│
├── backend/
│   ├── config.py
│   ├── requirements.txt
│   ├── __init__.py
│   │
│   ├── api/
│   │   ├── study_plan.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── __init__.py
│   │   └── api/
│   │       ├── upload.py
│   │       └── __init__.py
│   │
│   ├── services/
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── llm_service.py
│   │   ├── parser.py
│   │   ├── qdrant_service.py
│   │   ├── retrieval.py
│   │   └── __init__.py
│   │
│   └── uploads/
│
├── docs/
│   ├── architecture.md
│   └── setup.md
│
├── frontend/
│   ├── config.js
│   ├── error.html
│   ├── index.html
│   ├── result.html
│   ├── script.js
│   ├── styles.css
│   └── upload.html
│
└── tests/
    ├── test_chunking.py
    ├── test_embeddings_dim.py
    ├── test_endpoints.py
    ├── test_llm_service.py
    ├── test_parser.py
    └── test_qdrant_and_retrieval.py
```

There used to be duplicated `backend/app/config.py`, `backend/app/services/`
etc. — these were dead code (never imported by the running app) and have
been removed as part of consolidating on a single `backend.*` import path.

---

## ⚙ Setup

```bash
pip install -r backend/requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY, QDRANT_URL, QDRANT_API_KEY
```

Run the backend:

```bash
uvicorn backend.app.main:app --reload
```

Open the frontend by serving `files/` with any static server (or opening
`files/upload.html` directly) — e.g.:

```bash
python -m http.server 5500 --directory files
```

`files/config.js` defaults `API_BASE_URL` to `http://localhost:8000`; change
it there for a non-local backend.

---

## 📡 API Endpoints

### `POST /upload`
Uploads and ingests a document: validates → extracts text → chunks →
embeds → stores in Qdrant.

Request: multipart form, field `file` (PDF/TXT/DOCX, ≤10MB)

Response:
```json
{
  "document_id": "uuid",
  "filename": "notes.pdf",
  "characters": 12345,
  "total_chunks": 18
}
```

### `POST /study-plan`
Retrieves relevant chunks for a topic (optionally scoped to a
`document_id`) and generates a grounded study plan.

Request:
```json
{ "topic": "photosynthesis", "top_k": 5, "document_id": "uuid" }
```

Response:
```json
{
  "topic": "photosynthesis",
  "summary": "...",
  "estimated_total_hours": 4,
  "days": [{ "day": 1, "focus": "...", "tasks": ["..."], "estimated_hours": 2 }],
  "retrieval": {
    "chunks_retrieved": 5,
    "sources": [{ "filename": "notes.pdf", "chunk_index": 2, "score": 0.81, "text": "..." }]
  }
}
```

No coverage score, "topics covered/missing", or similar numbers are
fabricated — the frontend only renders values the backend actually computed.

---

## ⚠️ Known limitations (MVP, being upfront about them)

- **Isolation is per-document, not per-user-session.** Every uploaded file
  gets a `document_id`, and `/study-plan` filters retrieval to that ID when
  provided — so one upload's chunks won't leak into another's results.
  There's no authentication, so this isn't the same guarantee as a real
  multi-user session boundary.
- Uploaded files are written to `backend/uploads/` and not automatically
  cleaned up.
- CORS defaults are permissive for local dev (`CORS_ORIGINS` in `.env`) —
  tighten before any real deployment.

---

## 🧪 Tests

```bash
python -m pytest          # unit + endpoint tests, external services mocked
python test_pipeline.py   # manual end-to-end smoke test (needs real Qdrant + Groq creds)
```

`test_pipeline.py` runs against a dedicated `<collection>_test` Qdrant
collection, never the real one.

---

## 📄 License

MIT License
