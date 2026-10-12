# """
# AskDSA Stage-2 scraper — GeeksforGeeks /dsa/ article pages -> wide CSV.

# Input : Datasets/all_problem_links.csv   (columns: category, link)
# Output: Datasets/Dataset with problems/problems.csv

# Layout: ONE row per problem. Up to 4 approaches, each with its own columns:
#     approach{i}_heading, approach{i}_solution,
#     approach{i}_cpp, approach{i}_c, approach{i}_java,
#     approach{i}_python, approach{i}_csharp, approach{i}_javascript,
#     approach{i}_tc, approach{i}_sc        (tc/sc filled with "NULL" for now)

# Run (from repo root):
#     python "Data Collection\\problem_data_scrapper.py" --inspect "<one gfg url>"   # test 1 page
#     python "Data Collection\\problem_data_scrapper.py" --limit 5                   # trial on first 5
#     python "Data Collection\\problem_data_scrapper.py"                             # full run (resumable)
# """
# import argparse, csv, re, random, time
# from datetime import datetime, timezone
# from pathlib import Path

# from bs4 import BeautifulSoup, Tag

# # ---------------- config ----------------
# # INPUT_CSV  = Path("Datasets/all_problem_links.csv")
# # OUTPUT_CSV = Path("Datasets/Dataset with problems/problems.csv")

# INPUT_CSV  = Path("all_problem_links.csv")
# OUTPUT_CSV = Path("problems2.csv")

# MAX_APPROACHES = 4
# LANGS = ["cpp", "c", "java", "python", "csharp", "javascript"]  # column order

# CONTENT_SEL = "div.article--viewer_content"      # stable half of the hashed class
# APPROACH_RE = re.compile(r"\b(approach|method|naive|brute|optimal|efficient|"
#                          r"better|expected|using)\b", re.I)

# # GfG's data-code-lang values -> our column keys (robust to minor variants)
# LANG_MAP = {
#     "cpp": "cpp", "c++": "cpp",
#     "c": "c",
#     "java": "java",
#     "python": "python", "python3": "python", "py": "python",
#     "csharp": "csharp", "c#": "csharp", "cs": "csharp",
#     "javascript": "javascript", "js": "javascript", "nodejs": "javascript",
# }

# MIN_DELAY, MAX_DELAY = 2.0, 4.0
# PAGE_TIMEOUT_MS = 30_000
# MAX_RETRIES = 3
# HEADLESS = True
# USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# # ---------------- helpers ----------------
# def clean(t: str) -> str:
#     return re.sub(r"[ \t\u00a0]+", " ", (t or "")).replace("\r", "").strip()

# def clean_code(t: str) -> str:
#     if not t:
#         return ""
#     t = t.replace("\r", "")
#     t = re.sub(r"[ \t]+\n", "\n", t)     # trailing spaces per line
#     t = re.sub(r"\n{3,}", "\n\n", t)     # collapse big gaps
#     return t.strip("\n")

# def is_approach_heading(el) -> bool:
#     return (isinstance(el, Tag) and el.name in ("h2", "h3")
#             and bool(APPROACH_RE.search(el.get_text(" "))))

# def main_children(root):
#     """Direct child tags of the article body, across all html-chunk blocks, in order."""
#     chunks = root.select("div.html-chunk") or [root]
#     out = []
#     for ch in chunks:
#         out.extend(c for c in ch.children if isinstance(c, Tag))
#     return out

# # ---------------- parsing ----------------
# def extract_codes(gfg_tabs) -> dict:
#     """{lang_key: source} from every <gfg-panel data-code-lang=...> in a code widget."""
#     codes = {}
#     for panel in gfg_tabs.find_all("gfg-panel"):
#         raw = (panel.get("data-code-lang") or "").strip().lower()
#         lang = LANG_MAP.get(raw)
#         if not lang:
#             continue
#         code_el = panel.find("code") or panel.find("pre")
#         if code_el is None:
#             continue
#         src = clean_code(code_el.get_text())
#         if src and lang not in codes:
#             codes[lang] = src
#     return codes

# def section_to_approach(heading_el, sibs) -> dict:
#     text_bits, codes = [], {}
#     for el in sibs:
#         if el.name == "gfg-tabs":
#             found = extract_codes(el)
#             if found:
#                 codes = found
#             continue
#         classes = el.get("class") or []
#         if el.name == "div" and (el.get("id") == "table_of_content" or "code-output" in classes):
#             continue
#         if el.name in ("blockquote", "p", "ul"):
#             txt = clean(el.get_text(" "))
#             if txt:
#                 text_bits.append(txt)
#     return {"heading": clean(heading_el.get_text(" ")),
#             "solution": "\n".join(text_bits),
#             "codes": codes}

# def parse_problem(html: str, url: str, category: str) -> dict:
#     soup = BeautifulSoup(html, "html.parser")

#     h1 = soup.find("h1")
#     title = clean(h1.get_text()) if h1 else ""

#     root = soup.select_one(CONTENT_SEL) or soup.body or soup
#     children = main_children(root)

#     approach_idx = [i for i, el in enumerate(children) if is_approach_heading(el)]
#     first = approach_idx[0] if approach_idx else len(children)

#     # description + examples live before the first approach heading
#     desc_bits, example_bits = [], []
#     for el in children[:first]:
#         if el.name == "p":
#             t = clean(el.get_text(" "))
#             if t and not re.match(r"(?i)^table of content", t):
#                 desc_bits.append(t)
#         elif el.name == "blockquote":
#             t = clean(el.get_text(" "))
#             if t:
#                 example_bits.append(t)

#     approaches = []
#     for k, idx in enumerate(approach_idx):
#         end = approach_idx[k + 1] if k + 1 < len(approach_idx) else len(children)
#         approaches.append(section_to_approach(children[idx], children[idx + 1:end]))

#     return {"category": category, "url": url, "title": title,
#             "description": " ".join(desc_bits), "examples": "\n---\n".join(example_bits),
#             "num_approaches": len(approaches), "approaches": approaches,
#             "status": "ok" if title else "empty",
#             "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

# # ---------------- CSV shaping ----------------
# META = ["category", "url", "title", "description", "examples",
#         "num_approaches", "status", "scraped_at"]

# def build_fieldnames():
#     cols = list(META)
#     for i in range(1, MAX_APPROACHES + 1):
#         cols += [f"approach{i}_heading", f"approach{i}_solution"]
#         cols += [f"approach{i}_{lang}" for lang in LANGS]
#         cols += [f"approach{i}_tc", f"approach{i}_sc"]
#     return cols

# FIELDNAMES = build_fieldnames()

# def record_to_row(rec: dict) -> dict:
#     row = {k: rec.get(k, "") for k in META}
#     for i in range(1, MAX_APPROACHES + 1):
#         a = rec["approaches"][i - 1] if i - 1 < len(rec["approaches"]) else None
#         row[f"approach{i}_heading"]  = a["heading"] if a else ""
#         row[f"approach{i}_solution"] = a["solution"] if a else ""
#         for lang in LANGS:
#             row[f"approach{i}_{lang}"] = (a["codes"].get(lang, "") if a else "")
#         row[f"approach{i}_tc"] = "NULL" if a else ""
#         row[f"approach{i}_sc"] = "NULL" if a else ""
#     return row

# # ---------------- fetch (Playwright imported lazily) ----------------
# def fetch_html(page, url: str) -> str:
#     last = None
#     for attempt in range(1, MAX_RETRIES + 1):
#         try:
#             page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
#             page.wait_for_timeout(1000)
#             page.mouse.wheel(0, 8000)         # trigger lazy-loaded code widgets
#             page.wait_for_timeout(600)
#             return page.content()
#         except Exception as e:
#             last = e
#             time.sleep(1.5 * attempt)
#     raise RuntimeError(f"failed after {MAX_RETRIES} tries: {last}")

# # ---------------- IO ----------------
# def load_links(path):
#     with open(path, newline="", encoding="utf-8") as f:
#         rows = []
#         for r in csv.DictReader(f):
#             url = clean(r.get("link") or r.get("url") or "")
#             if url.startswith("http"):
#                 rows.append({"url": url, "category": clean(r.get("category", ""))})
#     return rows

# def load_done(path):
#     if not path.exists():
#         return set()
#     with open(path, newline="", encoding="utf-8") as f:
#         return {r["url"] for r in csv.DictReader(f) if r.get("status") == "ok"}

# # ---------------- runners ----------------
# def run(limit=None):
#     from playwright.sync_api import sync_playwright
#     links = load_links(INPUT_CSV)
#     if limit:
#         links = links[:limit]
#     done = load_done(OUTPUT_CSV)
#     todo = [l for l in links if l["url"] not in done]
#     print(f"{len(links)} links | {len(done)} done | {len(todo)} to scrape")
#     OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
#     new = not OUTPUT_CSV.exists()
#     with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as fout, sync_playwright() as p:
#         w = csv.DictWriter(fout, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
#         if new:
#             w.writeheader()
#         browser = p.chromium.launch(headless=HEADLESS)
#         pg = browser.new_page(user_agent=USER_AGENT)
#         pg.set_default_timeout(PAGE_TIMEOUT_MS)
#         for i, link in enumerate(todo, 1):
#             try:
#                 rec = parse_problem(fetch_html(pg, link["url"]), link["url"], link["category"])
#             except Exception as e:
#                 rec = {"category": link["category"], "url": link["url"], "title": "",
#                        "description": "", "examples": "", "num_approaches": 0,
#                        "approaches": [], "status": f"error: {e}",
#                        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
#             w.writerow(record_to_row(rec)); fout.flush()
#             print(f"[{i}/{len(todo)}] {rec['status'][:22]:22} {rec['num_approaches']} appr  {link['url']}")
#             time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
#         browser.close()
#     print(f"\nDone -> {OUTPUT_CSV}")

# def inspect(url):
#     from playwright.sync_api import sync_playwright
#     with sync_playwright() as p:
#         b = p.chromium.launch(headless=HEADLESS)
#         pg = b.new_page(user_agent=USER_AGENT)
#         pg.set_default_timeout(PAGE_TIMEOUT_MS)
#         html = fetch_html(pg, url)
#         b.close()
#     rec = parse_problem(html, url, "")
#     print("TITLE          :", rec["title"])
#     print("STATUS         :", rec["status"])
#     print("NUM APPROACHES :", rec["num_approaches"])
#     print("\nDESCRIPTION:\n", rec["description"][:400])
#     print("\nEXAMPLES:\n", rec["examples"][:400])
#     for i, a in enumerate(rec["approaches"], 1):
#         print(f"\n=== APPROACH {i}: {a['heading']} ===")
#         print("SOLUTION:", a["solution"][:300])
#         for lang in LANGS:
#             code = a["codes"].get(lang, "")
#             preview = (" | " + code[:60].replace("\n", " ⏎ ")) if code else " | (none)"
#             print(f"   [{lang:10}] {len(code):4d} chars{preview}")

# if __name__ == "__main__":
#     ap = argparse.ArgumentParser()
#     ap.add_argument("--inspect", help="parse a single URL and print the result")
#     ap.add_argument("--limit", type=int, help="only scrape the first N links (trial run)")
#     args = ap.parse_args()
#     if args.inspect:
#         inspect(args.inspect)
#     else:
#         run(limit=args.limit)







"""
AskDSA Stage-2 scraper — GeeksforGeeks /dsa/ article pages -> wide CSV.

Input : all_problem_links.csv   (columns: category, link)
Output: problems2.csv           (one row per problem)

Layout: ONE row per problem. Up to 4 approaches, each with its own columns:
    approach{i}_heading, approach{i}_solution,
    approach{i}_cpp, approach{i}_c, approach{i}_java,
    approach{i}_python, approach{i}_csharp, approach{i}_javascript,
    approach{i}_tc, approach{i}_sc        (tc/sc filled with "NULL" for now)

Run (from repo root):
    python "Data Collection\\problem_data_scrapper.py" --inspect "<one gfg url>"   # test 1 page

    # Batch scraping by index range (end is EXCLUSIVE). Output appends, so batches stack up:
    python "Data Collection\\problem_data_scrapper.py" --end 100                   # links 0..99
    python "Data Collection\\problem_data_scrapper.py" --start 100 --end 200       # links 100..199
    python "Data Collection\\problem_data_scrapper.py" --start 200 --end 300       # links 200..299
    python "Data Collection\\problem_data_scrapper.py" --limit 5                   # first 5 (quick test)
    python "Data Collection\\problem_data_scrapper.py"                             # everything (resumable)

Already-scraped links (status "ok") are always skipped, so re-running a range is safe.
NOTE: index ranges rely on the row order of all_problem_links.csv — don't regenerate
that file midway through, or positions will shift.
"""
import argparse, csv, re, random, time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, Tag

# ---------------- config ----------------
# INPUT_CSV  = Path("Datasets/all_problem_links.csv")
# OUTPUT_CSV = Path("Datasets/Dataset with problems/problems.csv")

INPUT_CSV  = Path("all_problem_links.csv")
OUTPUT_CSV = Path("problems.csv")

MAX_APPROACHES = 4
LANGS = ["cpp", "c", "java", "python", "csharp", "javascript"]  # column order

CONTENT_SEL = "div.article--viewer_content"      # stable half of the hashed class
APPROACH_RE = re.compile(r"\b(approach|method|naive|brute|optimal|efficient|"
                         r"better|expected|using)\b", re.I)

# GfG's data-code-lang values -> our column keys (robust to minor variants)
LANG_MAP = {
    "cpp": "cpp", "c++": "cpp",
    "c": "c",
    "java": "java",
    "python": "python", "python3": "python", "py": "python",
    "csharp": "csharp", "c#": "csharp", "cs": "csharp",
    "javascript": "javascript", "js": "javascript", "nodejs": "javascript",
}

# ---- politeness / throttling (tune these to taste) ----
MIN_DELAY, MAX_DELAY = 3.0, 7.0          # random pause between pages (seconds)
LONG_BREAK_EVERY = 20                     # take a longer break every N scraped pages
LONG_BREAK_MIN, LONG_BREAK_MAX = 10.0, 15.0   # length of that longer break (seconds)
CONSECUTIVE_ERROR_LIMIT = 5               # stop the run if this many pages fail back-to-back

PAGE_TIMEOUT_MS = 30_000
MAX_RETRIES = 3
HEADLESS = True
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# ---------------- helpers ----------------
def clean(t: str) -> str:
    return re.sub(r"[ \t\u00a0]+", " ", (t or "")).replace("\r", "").strip()

def clean_code(t: str) -> str:
    if not t:
        return ""
    t = t.replace("\r", "")
    t = re.sub(r"[ \t]+\n", "\n", t)     # trailing spaces per line
    t = re.sub(r"\n{3,}", "\n\n", t)     # collapse big gaps
    return t.strip("\n")

def is_approach_heading(el) -> bool:
    return (isinstance(el, Tag) and el.name in ("h2", "h3")
            and bool(APPROACH_RE.search(el.get_text(" "))))

def main_children(root):
    """Direct child tags of the article body, across all html-chunk blocks, in order."""
    chunks = root.select("div.html-chunk") or [root]
    out = []
    for ch in chunks:
        out.extend(c for c in ch.children if isinstance(c, Tag))
    return out

# ---------------- parsing ----------------
def extract_codes(gfg_tabs) -> dict:
    """{lang_key: source} from every <gfg-panel data-code-lang=...> in a code widget."""
    codes = {}
    for panel in gfg_tabs.find_all("gfg-panel"):
        raw = (panel.get("data-code-lang") or "").strip().lower()
        lang = LANG_MAP.get(raw)
        if not lang:
            continue
        code_el = panel.find("code") or panel.find("pre")
        if code_el is None:
            continue
        src = clean_code(code_el.get_text())
        if src and lang not in codes:
            codes[lang] = src
    return codes

def section_to_approach(heading_el, sibs) -> dict:
    text_bits, codes = [], {}
    for el in sibs:
        if el.name == "gfg-tabs":
            found = extract_codes(el)
            if found:
                codes = found
            continue
        classes = el.get("class") or []
        if el.name == "div" and (el.get("id") == "table_of_content" or "code-output" in classes):
            continue
        if el.name in ("blockquote", "p", "ul"):
            txt = clean(el.get_text(" "))
            if txt:
                text_bits.append(txt)
    return {"heading": clean(heading_el.get_text(" ")),
            "solution": "\n".join(text_bits),
            "codes": codes}

def parse_problem(html: str, url: str, category: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    title = clean(h1.get_text()) if h1 else ""

    root = soup.select_one(CONTENT_SEL) or soup.body or soup
    children = main_children(root)

    approach_idx = [i for i, el in enumerate(children) if is_approach_heading(el)]
    first = approach_idx[0] if approach_idx else len(children)

    # description + examples live before the first approach heading
    desc_bits, example_bits = [], []
    for el in children[:first]:
        if el.name == "p":
            t = clean(el.get_text(" "))
            if t and not re.match(r"(?i)^table of content", t):
                desc_bits.append(t)
        elif el.name == "blockquote":
            t = clean(el.get_text(" "))
            if t:
                example_bits.append(t)

    approaches = []
    for k, idx in enumerate(approach_idx):
        end = approach_idx[k + 1] if k + 1 < len(approach_idx) else len(children)
        approaches.append(section_to_approach(children[idx], children[idx + 1:end]))

    return {"category": category, "url": url, "title": title,
            "description": " ".join(desc_bits), "examples": "\n---\n".join(example_bits),
            "num_approaches": len(approaches), "approaches": approaches,
            "status": "ok" if title else "empty",
            "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

# ---------------- CSV shaping ----------------
META = ["category", "url", "title", "description", "examples",
        "num_approaches", "status", "scraped_at"]

def build_fieldnames():
    cols = list(META)
    for i in range(1, MAX_APPROACHES + 1):
        cols += [f"approach{i}_heading", f"approach{i}_solution"]
        cols += [f"approach{i}_{lang}" for lang in LANGS]
        cols += [f"approach{i}_tc", f"approach{i}_sc"]
    return cols

FIELDNAMES = build_fieldnames()

def record_to_row(rec: dict) -> dict:
    row = {k: rec.get(k, "") for k in META}
    for i in range(1, MAX_APPROACHES + 1):
        a = rec["approaches"][i - 1] if i - 1 < len(rec["approaches"]) else None
        row[f"approach{i}_heading"]  = a["heading"] if a else ""
        row[f"approach{i}_solution"] = a["solution"] if a else ""
        for lang in LANGS:
            row[f"approach{i}_{lang}"] = (a["codes"].get(lang, "") if a else "")
        row[f"approach{i}_tc"] = "NULL" if a else ""
        row[f"approach{i}_sc"] = "NULL" if a else ""
    return row

# ---------------- fetch (Playwright imported lazily) ----------------
def fetch_html(page, url: str) -> str:
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            page.wait_for_timeout(random.randint(900, 1600))   # small random settle
            page.mouse.wheel(0, 8000)                           # trigger lazy code widgets
            page.wait_for_timeout(random.randint(500, 900))
            return page.content()
        except Exception as e:
            last = e
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"failed after {MAX_RETRIES} tries: {last}")

# ---------------- IO ----------------
def load_links(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = []
        for r in csv.DictReader(f):
            url = clean(r.get("link") or r.get("url") or "")
            if url.startswith("http"):
                rows.append({"url": url, "category": clean(r.get("category", ""))})
    return rows

def load_done(path):
    if not path.exists():
        return set()
    with open(path, newline="", encoding="utf-8") as f:
        return {r["url"] for r in csv.DictReader(f) if r.get("status") == "ok"}

# ---------------- runners ----------------
def run(start=0, end=None):
    from playwright.sync_api import sync_playwright
    links = load_links(INPUT_CSV)
    total = len(links)
    batch = links[start:end]
    shown_end = end if end is not None else total
    done = load_done(OUTPUT_CSV)
    todo = [l for l in batch if l["url"] not in done]
    print(f"{total} links total | slice [{start}:{shown_end}] = {len(batch)} | "
          f"{len(batch) - len(todo)} already done | {len(todo)} to scrape")
    if not todo:
        print("Nothing to do for this range.")
        return

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    new = not OUTPUT_CSV.exists()
    consecutive_errors = 0
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as fout, sync_playwright() as p:
        w = csv.DictWriter(fout, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
        if new:
            w.writeheader()
        browser = p.chromium.launch(headless=HEADLESS)
        pg = browser.new_page(user_agent=USER_AGENT)
        pg.set_default_timeout(PAGE_TIMEOUT_MS)
        for i, link in enumerate(todo, 1):
            try:
                rec = parse_problem(fetch_html(pg, link["url"]), link["url"], link["category"])
                consecutive_errors = 0
            except Exception as e:
                rec = {"category": link["category"], "url": link["url"], "title": "",
                       "description": "", "examples": "", "num_approaches": 0,
                       "approaches": [], "status": f"error: {e}",
                       "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                consecutive_errors += 1
            w.writerow(record_to_row(rec)); fout.flush()
            print(f"[{i}/{len(todo)}] {rec['status'][:22]:22} {rec['num_approaches']} appr  {link['url']}")

            # back off if the site seems to be blocking us
            if consecutive_errors >= CONSECUTIVE_ERROR_LIMIT:
                print(f"\n!! {consecutive_errors} failures in a row — stopping to avoid a ban.")
                print("   Wait a while, then re-run the same range; finished links are skipped.")
                break

            # polite random pause between pages, plus a longer break periodically
            if i < len(todo):
                time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
                if i % LONG_BREAK_EVERY == 0:
                    pause = random.uniform(LONG_BREAK_MIN, LONG_BREAK_MAX)
                    print(f"   … taking a {pause:.0f}s break after {i} pages …")
                    time.sleep(pause)
        browser.close()
    print(f"\nDone -> {OUTPUT_CSV}")

def inspect(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=HEADLESS)
        pg = b.new_page(user_agent=USER_AGENT)
        pg.set_default_timeout(PAGE_TIMEOUT_MS)
        html = fetch_html(pg, url)
        b.close()
    rec = parse_problem(html, url, "")
    print("TITLE          :", rec["title"])
    print("STATUS         :", rec["status"])
    print("NUM APPROACHES :", rec["num_approaches"])
    print("\nDESCRIPTION:\n", rec["description"][:400])
    print("\nEXAMPLES:\n", rec["examples"][:400])
    for i, a in enumerate(rec["approaches"], 1):
        print(f"\n=== APPROACH {i}: {a['heading']} ===")
        print("SOLUTION:", a["solution"][:300])
        for lang in LANGS:
            code = a["codes"].get(lang, "")
            preview = (" | " + code[:60].replace("\n", " ⏎ ")) if code else " | (none)"
            print(f"   [{lang:10}] {len(code):4d} chars{preview}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", help="parse a single URL and print the result")
    ap.add_argument("--start", type=int, default=0, help="0-based start index into the links list")
    ap.add_argument("--end", type=int, help="end index (exclusive)")
    ap.add_argument("--limit", type=int, help="shortcut: scrape N links starting at --start")
    args = ap.parse_args()

    if args.inspect:
        inspect(args.inspect)
    else:
        start = args.start or 0
        end = args.end
        if args.limit is not None and end is None:
            end = start + args.limit
        run(start=start, end=end)