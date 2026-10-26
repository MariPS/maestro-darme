"""
Central project configuration: paths and settings shared by more than one module.
"""
from pathlib import Path

# This file is src/maestro/config.py: going up two folders (parents[2]) gives the
# project root, whatever folder the scripts are launched from.
ROOT = Path(__file__).resolve().parents[2]

CORPUS_RAW = ROOT / "corpus" / "raw"                # pages as downloaded
CORPUS_PROCESSED = ROOT / "corpus" / "processed"    # parsed passages (JSONL)

# Used by the downloader (page URLs) and by the parser (image URLs).
WIKTENAUER_BASE = "https://wiktenauer.com"

# Multilingual embedding model: the same one must be used to index and to search.
EMBED_MODEL = "BAAI/bge-m3"

CHROMA_DIR = ROOT / ".chroma"       # vector database (generated, not versioned)
COLLECTION_NAME = "passages"