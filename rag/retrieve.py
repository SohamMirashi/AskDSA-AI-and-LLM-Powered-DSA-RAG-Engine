"""Load the FAISS index and return the top-k most relevant chunks for a query.

As a script, runs a quick demo search:
    python rag\\retrieve.py "how to find leaders in an array"
"""
import pickle, sys
from pathlib import Path
import faiss
from sentence_transformers import SentenceTransformer

INDEX_PATH = Path("store/index.faiss")
META_PATH = Path("store/meta.pkl")

class Retriever:
    def __init__(self):
        if not INDEX_PATH.exists():
            raise SystemExit(f"Missing {INDEX_PATH} — run embed.py first")
        self.index = faiss.read_index(str(INDEX_PATH))
        meta = pickle.load(open(META_PATH, "rb"))
        self.chunks = meta["chunks"]
        self.q_instr = meta.get("query_instruction", "")
        self.model = SentenceTransformer(meta["model"])

    def search(self, query, k=5, chunk_type=None, problem_url=None):
        # If the student's current problem is known, ground DIRECTLY on its chunks
        # (problem statement first, then approaches in order) rather than hoping vector
        # search resurfaces that exact problem. k=0/None returns all of them.
        if problem_url:
            res = [dict(c) for c in self.chunks
                   if c["problem_url"] == problem_url
                   and (not chunk_type or c["chunk_type"] == chunk_type)]
            res.sort(key=lambda c: (c["chunk_type"] != "problem", c["approach_index"]))
            for c in res:
                c["score"] = 1.0
            return res[:k] if k else res

        # Otherwise semantic search across the whole knowledge base.
        q = self.model.encode([self.q_instr + query],
                              normalize_embeddings=True).astype("float32")
        fetch = k * 5 if chunk_type else k          # over-fetch so filter still yields k
        scores, idx = self.index.search(q, min(fetch, self.index.ntotal))
        out = []
        for s, i in zip(scores[0], idx[0]):
            if i < 0:
                continue
            c = dict(self.chunks[i])
            c["score"] = float(s)
            if chunk_type and c["chunk_type"] != chunk_type:
                continue
            out.append(c)
            if len(out) >= k:
                break
        return out

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "sliding window maximum"
    r = Retriever()
    print(f"Query: {query!r}\n")
    for c in r.search(query, k=5):
        tag = c["approach_heading"] or "(problem statement)"
        print(f"[{c['score']:.3f}] {c['chunk_type']:8} {c['title']}  —  {tag}")