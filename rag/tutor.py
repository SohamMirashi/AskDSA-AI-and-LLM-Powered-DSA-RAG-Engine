"""Grounded DSA tutor: retrieve relevant context, then ask the LLM to guide the
student with progressive hints instead of dumping the full solution.

    python rag\\tutor.py "I'm stuck finding leaders in an array"            # level 1 (nudge)
    python rag\\tutor.py "explain the optimal approach" --level 3
    python rag\\tutor.py "give me the full solution" --level 4
    python rag\\tutor.py "how do I approach this?" --url "<gfg problem url>" --level 2
    python rag\\tutor.py "..." --dry-run        # show retrieval + prompt, DON'T call the LLM
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))   # so 'import retrieve'/'import llm' work as a script
from retrieve import Retriever
import llm

LEVELS = {
    1: "Give ONE small nudge: restate the heart of the problem and ask a single guiding "
       "question. Do NOT name the approach, give steps, or any code.",
    2: "Describe the general strategy/pattern in plain words and name the technique. "
       "Still NO step-by-step and NO code.",
    3: "Give the step-by-step approach, and pseudocode if it helps. Do NOT give complete "
       "runnable code.",
    4: "Give the full explanation AND the complete code (Python unless the student asked "
       "for another language), including time and space complexity.",
}

# Short hints stay short (saves tokens); full solutions get room so they aren't cut off.
MAX_TOKENS = {1: 350, 2: 500, 3: 1200, 4: 2000}

SYSTEM = (
    "You are AskDSA, a Data Structures & Algorithms interview tutor. "
    "Your job is to help the student UNDERSTAND and reach the solution themselves, not to "
    "hand over the answer. Ground every claim in the provided CONTEXT; if the context does "
    "not cover something, say so rather than inventing it. "
    "Never reveal more than the requested hint level asks for. "
    "FORMATTING: Do NOT use LaTeX or math delimiters ($, $$, \\( \\), \\[ \\]) or commands "
    "like \\binom, \\frac, \\times, \\text. Write math in plain text: combinations as "
    "C(n, k), multiply as ×, powers as ^ (e.g. 10^9 + 7), fractions as a/b."
)

def build_context(results):
    blocks = []
    for c in results:
        head = c["title"] + (f" — {c['approach_heading']}" if c["approach_heading"] else "")
        block = f"### {head}\n{c['text']}"
        if c.get("code"):
            lang = "python" if "python" in c["code"] else next(iter(c["code"]))
            block += f"\n\n[{lang} solution]\n{c['code'][lang]}"
        blocks.append(block)
    return "\n\n---\n\n".join(blocks)

def tutor(query, level=1, k=4, problem_url=None, dry_run=False, retriever=None):
    r = retriever or Retriever() # the API passes a shared, pre-loaded Retriever
    if problem_url:
        results = r.search(query, k=0, problem_url=problem_url)
        if not results:                       # URL not in our DB -> fall back to semantic search
            results = r.search(query, k=k)
    else:
        results = r.search(query, k=k)
    context = build_context(results)
    user = (f"CONTEXT (retrieved from the DSA knowledge base):\n{context}\n\n"
            f"STUDENT QUESTION: {query}\n\n"
            f"RESPOND AT HINT LEVEL {level}: {LEVELS.get(level, LEVELS[1])}")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": user}]
    if dry_run:
        print("=== retrieved ===")
        for c in results:
            print(f"  [{c['score']:.3f}] {c['title']} / {c['approach_heading'] or 'problem'}")
        print("\n=== prompt sent to the model (truncated) ===\n")
        print(user[:2500])
        return None
    return llm.chat(messages, temperature=0.3, max_tokens=MAX_TOKENS.get(level, 1000))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--level", type=int, default=1, choices=[1, 2, 3, 4])
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--url", help="ground on a specific problem's URL (what the extension will pass)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    out = tutor(a.query, level=a.level, k=a.k, problem_url=a.url, dry_run=a.dry_run)
    if out:
        print(out)