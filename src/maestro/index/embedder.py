"""
Embeddings: from texts to vectors.

An embedding is a list of numbers (1024 for bge-m3) that represents the meaning of a
text: texts with a similar meaning get vectors pointing in similar directions.
Vectors are normalised (length 1), so their similarity is just their dot product.
"""
from maestro import config

_model = None   # loaded once: loading takes a few seconds and about 2 GB of memory


def load_model():
    """The embedding model, loaded the first time it is needed."""
    global _model
    if _model is None:
        # A heavy import (it brings PyTorch): done here, only when really needed.
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBED_MODEL)
    return _model


def embed(texts, show_progress=False):
    """One normalised vector (a list of floats) per text."""
    vectors = load_model().encode(
        texts,
        batch_size=8,                 # texts processed together: a balance between speed and memory
        normalize_embeddings=True,    # length 1, so cosine similarity = dot product
        show_progress_bar=show_progress,
    )
    return vectors.tolist()           # plain Python lists instead of a NumPy array