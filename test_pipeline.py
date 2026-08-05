"""
Quick manual test of the embed -> store -> retrieve -> generate pipeline.
Uses fake sample chunks since Member 2's real chunking.py doesn't exist yet.
Clears the collection first so repeated runs don't pile up duplicates.
Run with: python test_pipeline.py
"""

import json

from backend.config import settings
from backend.services.embeddings import embed_texts
from backend.services.llm_service import generate_study_plan
from backend.services.qdrant_service import ensure_collection, get_client, store_embeddings
from backend.services.retrieval import build_context_string, retrieve_relevant_chunks

sample_chunks = [
    "Photosynthesis is the process by which plants convert light energy into chemical energy.",
    "The light-dependent reactions occur in the thylakoid membrane and produce ATP and NADPH.",
    "The Calvin cycle uses ATP and NADPH to fix carbon dioxide into glucose.",
    "Mitochondria are the powerhouse of the cell, producing ATP through respiration.",
]

print("Clearing old test data...")
client = get_client()
existing = [c.name for c in client.get_collections().collections]
if settings.QDRANT_COLLECTION in existing:
    client.delete_collection(settings.QDRANT_COLLECTION)

print("Embedding sample chunks...")
vectors = embed_texts(sample_chunks)
print(f"Got {len(vectors)} vectors of dimension {len(vectors[0])}")

print("Ensuring collection exists...")
ensure_collection()

print("Storing embeddings...")
ids = store_embeddings(sample_chunks, vectors)
print(f"Stored {len(ids)} points")

query = "how do plants make energy from sunlight"
print(f"\nSearching for: '{query}'")
results = retrieve_relevant_chunks(query, top_k=2)
for r in results:
    print(f"  score={r['score']:.4f}  text={r['text']}")

context = build_context_string(results)
print("\nGenerating study plan with Gemini...")
plan = generate_study_plan("photosynthesis", context)
print(json.dumps(plan, indent=2))