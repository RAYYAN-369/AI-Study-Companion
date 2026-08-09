"""
Manual smoke test of the embed -> store -> retrieve -> generate pipeline,
using sample chunks (not a real upload).

IMPORTANT: this runs against a dedicated TEST collection
(f"{QDRANT_COLLECTION}_test"), never the real collection, so running it
cannot destroy production data from real uploads.

Run with: python test_pipeline.py
(requires QDRANT_URL/QDRANT_API_KEY and GROQ_API_KEY to be set in .env)
"""

import json

from backend.config import settings
from backend.services.embeddings import embed_texts
from backend.services.llm_service import generate_study_plan
from backend.services.qdrant_service import ensure_collection, get_client, store_embeddings
from backend.services.retrieval import build_context_string, retrieve_relevant_chunks

TEST_COLLECTION = f"{settings.QDRANT_COLLECTION}_test"

sample_chunks = [
    "Photosynthesis is the process by which plants convert light energy into chemical energy.",
    "The light-dependent reactions occur in the thylakoid membrane and produce ATP and NADPH.",
    "The Calvin cycle uses ATP and NADPH to fix carbon dioxide into glucose.",
    "Mitochondria are the powerhouse of the cell, producing ATP through respiration.",
]

print(f"Clearing old data in test collection '{TEST_COLLECTION}' (never the real collection)...")
client = get_client()
existing = [c.name for c in client.get_collections().collections]
if TEST_COLLECTION in existing:
    client.delete_collection(TEST_COLLECTION)

print("Embedding sample chunks...")
vectors = embed_texts(sample_chunks)
print(f"Got {len(vectors)} vectors of dimension {len(vectors[0])}")

print(f"Ensuring test collection '{TEST_COLLECTION}' exists...")
ensure_collection(collection_name=TEST_COLLECTION)

print("Storing embeddings...")
ids = store_embeddings(sample_chunks, vectors, collection_name=TEST_COLLECTION)
print(f"Stored {len(ids)} points")

query = "how do plants make energy from sunlight"
print(f"\nSearching for: '{query}'")
results = retrieve_relevant_chunks(query, top_k=2, collection_name=TEST_COLLECTION)
for r in results:
    print(f"  score={r['score']:.4f}  text={r['text']}")

context = build_context_string(results)
print("\nGenerating study plan with Groq...")
plan = generate_study_plan("photosynthesis", context)
print(json.dumps(plan, indent=2))
