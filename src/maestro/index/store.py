"""
The vector store: where passage vectors are saved and searched (Chroma, on disk).

For each passage Chroma keeps its id, its vector and a few simple fields usable as
filters. The full passage stays in the JSONL file and is looked up by id: Chroma
metadata accept only strings, numbers and booleans (no lists, no None), and the
corpus already has a single source of truth.
"""
import chromadb
from chromadb.config import Settings

from maestro import config
from maestro.parse.schemas import TreatisePassage


def open_collection(reset=False):
    """The collection of passage vectors; with reset=True it is rebuilt empty."""
    client = chromadb.PersistentClient(
        path=str(config.CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),   # Chroma sends usage statistics by default
    )
    if reset:
        try:
            client.delete_collection(config.COLLECTION_NAME)
        except Exception:
            pass   # it did not exist yet (the exact error type changes across Chroma versions)
    return client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},   # distance = 1 - cosine similarity
        embedding_function=None,             # vectors come from embedder.py, not from Chroma
    )


def add_passages(collection, passages, vectors, batch=100):
    """Store passages and their vectors, a batch at a time."""
    for i in range(0, len(passages), batch):
        part = passages[i:i + batch]
        collection.add(
            ids=[p.passage_id for p in part],
            embeddings=vectors[i:i + batch],
            metadatas=[{"treatise_id": p.treatise_id, "section": p.section,
                        "folio": p.folio or ""} for p in part],
        )


def load_passages():
    """All parsed passages, by id, from corpus/processed/*.jsonl."""
    passages = {}
    for path in sorted(config.CORPUS_PROCESSED.glob("*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                p = TreatisePassage.model_validate_json(line)
                passages[p.passage_id] = p
    return passages