"""Build the search index: one vector per passage, saved in Chroma (.chroma/)."""
import time

from maestro import config
from maestro.index import store
from maestro.index.embedder import embed
from maestro.index.search_text import search_text


passages = list(store.load_passages().values())
print(f"{len(passages)} passages to index")

start = time.time()
vectors = embed([search_text(p) for p in passages], show_progress=True)
print(f"{len(vectors)} vectors of {len(vectors[0])} numbers in {time.time() - start:.0f}s")

collection = store.open_collection(reset=True)      # rebuilt from scratch every time
store.add_passages(collection, passages, vectors)
print(f"collection '{config.COLLECTION_NAME}': {collection.count()} passages in {config.CHROMA_DIR.name}/")

# Check: a passage's own vector must find the passage itself, at distance 0
result = collection.query(query_embeddings=[vectors[0]], n_results=1)
print(f"check: {passages[0].passage_id} -> {result['ids'][0][0]} "
      f"(distance {result['distances'][0][0]:.4f})")