"""Turn problems.csv (wide, one row/problem) into retrieval chunks -> store/chunks.jsonl.

Two chunk types per problem:
  - "problem"  : title + description + examples
  - "approach" : title + approach heading + solution explanation (code kept in payload)

Only the `text` field gets embedded later; everything else is metadata the tutor uses.

Run (from repo root):
    python rag\\chunk.py                 # reads problems2.csv
    python rag\\chunk.py some_other.csv  # reads a different CSV
"""
import csv, json, re, sys
from pathlib import Path

INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("problems.csv")
OUT = Path("store/chunks.jsonl")

LANGS = ["cpp", "c", "java", "python", "csharp", "javascript"]
MAX_APPROACHES = 4

csv.field_size_limit(10_000_000)   # code cells can exceed the default field limit

def clean(s):
    return (s or "").strip()

def build_chunks(row):
    url = clean(row.get("url"))
    title = clean(row.get("title"))
    category = clean(row.get("category"))
    chunks = []

    # ---- problem chunk: what the problem asks ----
    desc = re.sub(r"\s*Examples?:?\s*$", "", clean(row.get("description")))
    examples = clean(row.get("examples"))
    ptext = f"{title}\n\n{desc}"
    if examples:
        ptext += f"\n\nExamples:\n{examples}"
    chunks.append({
        "chunk_id": f"{url}#problem",
        "problem_url": url, "title": title, "category": category,
        "chunk_type": "problem", "approach_index": 0,
        "approach_heading": "", "text": ptext.strip(), "code": {},
    })

    # ---- one chunk per approach: how to solve it ----
    for i in range(1, MAX_APPROACHES + 1):
        heading = clean(row.get(f"approach{i}_heading"))
        if not heading:
            continue
        solution = clean(row.get(f"approach{i}_solution"))
        code = {lang: clean(row.get(f"approach{i}_{lang}")) for lang in LANGS}
        code = {k: v for k, v in code.items() if v}       # drop empty languages
        text = f"{title}\nApproach: {heading}\n{solution}".strip()
        chunks.append({
            "chunk_id": f"{url}#approach{i}",
            "problem_url": url, "title": title, "category": category,
            "chunk_type": "approach", "approach_index": i,
            "approach_heading": heading, "text": text, "code": code,
        })
    return chunks

def main():
    if not INPUT.exists():
        sys.exit(f"Input not found: {INPUT}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n_rows = n_chunks = 0
    with open(INPUT, newline="", encoding="utf-8") as fin, \
         open(OUT, "w", encoding="utf-8") as fout:
        for row in csv.DictReader(fin):
            if clean(row.get("status")) != "ok":
                continue
            n_rows += 1
            for ch in build_chunks(row):
                fout.write(json.dumps(ch, ensure_ascii=False) + "\n")
                n_chunks += 1
    print(f"{n_rows} problems -> {n_chunks} chunks -> {OUT}")

if __name__ == "__main__":
    main()