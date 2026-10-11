"""Merge every CSV in 'Datasets/Dataset with links' into one deduped master file.
Category is taken from each filename (links_array_top_50.csv -> array_top_50)."""
import csv, glob, re, sys
from pathlib import Path

LINKS_DIR = Path("Datasets/Dataset with links")
# OUT = Path("Datasets/all_problem_links.csv")
OUT = Path("all_problem_links.csv")

def category_from_filename(path: str) -> str:
    return re.sub(r"^links_", "", Path(path).stem)

def main():
    files = sorted(glob.glob(str(LINKS_DIR / "*.csv")))
    if not files:
        sys.exit(f"No CSVs found in {LINKS_DIR}")
    seen, order = {}, []
    for f in files:
        cat = category_from_filename(f)
        with open(f, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            cols = reader.fieldnames or []
            url_col = next((c for c in cols if c.lower() in
                            ("link", "url", "links", "problem_url")), cols[0])
            for row in reader:
                url = (row.get(url_col) or "").strip()
                if url.startswith("http") and url not in seen:
                    seen[url] = cat
                    order.append(url)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["category", "link"])
        for url in order:
            w.writerow([seen[url], url])
    print(f"{len(files)} files -> {len(order)} unique links -> {OUT}")

if __name__ == "__main__":
    main()