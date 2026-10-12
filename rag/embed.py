"""Embed chunks -> FAISS vector index. Run after chunk.py.

    python rag\\embed.py

Outputs: store/index.faiss  (the vectors) and store/meta.pkl (the chunk payloads).
Re-run any time chunks.jsonl changes; it overwrites both files.
"""
import json, pickle, sys
from pathlib import Path
import faiss
from sentence_transformers import SentenceTransformer

CHUNKS = Path("store/chunks.jsonl")
INDEX_PATH = Path("store/index.faiss")
META_PATH = Path("store/meta.pkl")

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
# bge models retrieve best when the QUERY (not the passages) carries this instruction:
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
BATCH = 64

def main():
    if not CHUNKS.exists():
        sys.exit(f"Missing {CHUNKS} — run chunk.py first")
    chunks = [json.loads(l) for l in open(CHUNKS, encoding="utf-8")]
    texts = [c["text"] for c in chunks]
    print(f"Loaded {len(chunks)} chunks. Loading model {EMBED_MODEL} "
          f"(first run downloads it, ~130MB)...")
    model = SentenceTransformer(EMBED_MODEL)
    print("Encoding (the slow part — a few minutes on CPU)...")
    emb = model.encode(texts, batch_size=BATCH, normalize_embeddings=True,
                       show_progress_bar=True).astype("float32")
    index = faiss.IndexFlatIP(emb.shape[1])   # inner product on normalized vecs == cosine
    index.add(emb)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "wb") as f:
        pickle.dump({"model": EMBED_MODEL, "query_instruction": QUERY_INSTRUCTION,
                     "chunks": chunks}, f)
    print(f"Indexed {index.ntotal} vectors (dim {emb.shape[1]}) -> {INDEX_PATH}, {META_PATH}")

if __name__ == "__main__":
    main()