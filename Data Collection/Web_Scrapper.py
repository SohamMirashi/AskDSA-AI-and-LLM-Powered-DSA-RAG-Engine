import asyncio
import random
import re
import uuid
import pandas as pd

from collections import deque
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# SEED URLS
SEED_URLS = [
    "https://www.geeksforgeeks.org/dsa/array-data-structure-guide/",
    "https://www.geeksforgeeks.org/dsa/top-50-array-coding-problems-for-interviews/",
]

# USER AGENTS
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
]

visited_problem_urls = set()
request_counter = 0

# Delay
async def human_delay(a=2.5, b=6):
    await asyncio.sleep(random.uniform(a, b))

# Safe Request
async def safe_goto(page, url, retries=5):

    global request_counter

    for attempt in range(retries):

        try:
            print(f"[VISIT] {url}")

            await page.goto(
                url,
                timeout=60000,
                wait_until="networkidle"
            )

            await page.wait_for_timeout(5000)

            await human_delay()

            html = await page.content()

            print(html[:1000])

            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            # CAPTCHA detection
            if "captcha" in html.lower():
                # blocked_indicators = [
                # "verify you are human",
                # "cf-challenge",
                # "captcha",
                # "access denied",
                # "temporarily blocked",
                # "cloudflare"
                # ]

                # if any(x in html.lower() for x in blocked_indicators):

                #     print("[WARNING] Possible anti-bot page detected")

                #     # Save page for debugging
                #     with open("blocked_page.html", "w", encoding="utf-8") as f:
                #         f.write(html)

                #     return False

                request_counter += 1

            # periodic cooldown
            if request_counter % 7 == 0:
                cooldown = random.uniform(15, 35)
                print(f"[COOLDOWN] Sleeping {cooldown:.2f}s")
                await asyncio.sleep(cooldown)

            return True

        except Exception as e:

            wait = (2 ** attempt) + random.uniform(1, 3)

            print(f"[RETRY] {url}")
            print(f"Attempt {attempt + 1}/{retries}")
            print(f"Waiting {wait:.2f}s")
            print("ERROR:", e)

            await asyncio.sleep(wait)

    return False

# URL Filter
def is_problem_url(url: str):

    if not url:
        return False

    blacklist = [
        "/tag/",
        "/category/",
        "/author/",
        "/practice/",
        "/videos/",
        "/comments/",
        "/page/",
        "/feed/",
        "/about/",
        "/jobs/",
        "/write/",
        "/user/",
        "/basic-programming-problems/",
    ]

    if not url.startswith("https://www.geeksforgeeks.org/"):
        return False

    if any(x in url for x in blacklist):
        return False

    slug = (
        url.replace("https://www.geeksforgeeks.org/", "")
        .strip("/")
    )

    # avoid extremely small pages
    if len(slug.split("-")) < 3:
        return False

    return True

# COLLECT ALL PROBLEM LINKS
async def collect_problem_links(page, urls):

    problem_links = set()

    for url in urls:

        success = await safe_goto(page, url)

        if not success:
            continue

        html = await page.content()

        soup = BeautifulSoup(html, "lxml")

        for a in soup.find_all("a", href=True):

            href = a["href"]

            if is_problem_url(href):
                problem_links.add(href)

    return list(problem_links)

# ---------------------------------------------------------
# CLEAN TEXT
# ---------------------------------------------------------

def clean_text(text):

    if not text:
        return None

    text = re.sub(r"\n{2,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------
# TITLE
# ---------------------------------------------------------

def extract_title(soup):

    h1 = soup.find("h1")

    if h1:
        return clean_text(h1.get_text())

    title_tag = soup.find("title")

    if title_tag:
        return clean_text(
            title_tag.get_text()
            .replace(" - GeeksforGeeks", "")
        )

    return None


# ---------------------------------------------------------
# DIFFICULTY
# ---------------------------------------------------------

def extract_difficulty(soup):

    possible = ["easy", "medium", "hard"]

    for tag in soup.find_all(["span", "div", "p"]):

        text = tag.get_text(strip=True).lower()

        if text in possible:
            return text.capitalize()

    return None


# ---------------------------------------------------------
# TAGS
# ---------------------------------------------------------

def extract_tags(soup):

    tags = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if "/tag/" in href:

            tag_text = a.get_text(strip=True)

            if tag_text and tag_text not in tags:
                tags.append(tag_text)

    return tags


# ---------------------------------------------------------
# MAIN ARTICLE
# ---------------------------------------------------------

def get_article_container(soup):

    selectors = [
        ("div", {"class": re.compile(r"article", re.I)}),
        ("div", {"class": re.compile(r"content", re.I)}),
        ("article", {}),
    ]

    for tag, attrs in selectors:

        container = soup.find(tag, attrs)

        if container:
            return container

    return soup


# ---------------------------------------------------------
# STATEMENT
# ---------------------------------------------------------

def extract_problem_statement(soup):

    article = get_article_container(soup)

    for bad in article.find_all(
        ["script", "style", "nav", "aside"]
    ):
        bad.decompose()

    text = article.get_text("\n", strip=True)

    lines = [x.strip() for x in text.split("\n") if x.strip()]

    statement = []

    for line in lines:

        lower = line.lower()

        if re.match(
            r"^(example|examples|input|output|constraints)",
            lower
        ):
            break

        statement.append(line)

    return clean_text("\n".join(statement))


# ---------------------------------------------------------
# CONSTRAINTS
# ---------------------------------------------------------

def extract_constraints(soup):

    article = get_article_container(soup)

    text = article.get_text("\n", strip=True)

    lines = [x.strip() for x in text.split("\n") if x.strip()]

    constraints = []

    inside = False

    for line in lines:

        lower = line.lower()

        if lower.startswith("constraints"):
            inside = True
            continue

        if inside:

            if re.match(
                r"^(example|approach|solution|input|output)",
                lower
            ):
                break

            constraints.append(line)

    return clean_text("\n".join(constraints))


# ---------------------------------------------------------
# EXAMPLES
# ---------------------------------------------------------

def extract_examples(soup):

    article = get_article_container(soup)

    text = article.get_text("\n", strip=True)

    lines = [x.strip() for x in text.split("\n") if x.strip()]

    examples = []

    i = 0

    while i < len(lines):

        current = lines[i].lower()

        if current.startswith("input"):

            example = {
                "input": None,
                "output": None,
                "explanation": None,
            }

            example["input"] = (
                lines[i].split(":", 1)[-1].strip()
            )

            j = i + 1

            while j < min(i + 10, len(lines)):

                line = lines[j].lower()

                if line.startswith("output"):
                    example["output"] = (
                        lines[j]
                        .split(":", 1)[-1]
                        .strip()
                    )

                if line.startswith("explanation"):
                    example["explanation"] = (
                        lines[j]
                        .split(":", 1)[-1]
                        .strip()
                    )

                j += 1

            examples.append(example)

        i += 1

    return examples


# ---------------------------------------------------------
# CODE EXTRACTION
# ---------------------------------------------------------

def extract_code_blocks(soup):

    result = {
        "cpp": None,
        "java": None,
        "python": None,
        "javascript": None,
    }

    pres = soup.find_all("pre")

    for pre in pres:

        text = pre.get_text("\n", strip=True)

        classes = " ".join(pre.get("class", [])).lower()

        parent_classes = ""

        if pre.parent:
            parent_classes = " ".join(
                pre.parent.get("class", [])
            ).lower()

        full_class = classes + " " + parent_classes

        # CPP
        if (
            "cpp" in full_class
            or "c++" in full_class
        ):
            result["cpp"] = text

        # JAVA
        elif "java" in full_class:
            result["java"] = text

        # PYTHON
        elif (
            "python" in full_class
            or "py" in full_class
        ):
            result["python"] = text

        # JAVASCRIPT
        elif (
            "javascript" in full_class
            or "js" in full_class
        ):
            result["javascript"] = text

    return result


# ---------------------------------------------------------
# COMPLEXITIES
# ---------------------------------------------------------

def extract_complexities(text):

    tc = None
    sc = None

    tc_match = re.search(
        r"Time Complexity\s*[:\-]?\s*(.*)",
        text,
        re.I
    )

    sc_match = re.search(
        r"Space Complexity\s*[:\-]?\s*(.*)",
        text,
        re.I
    )

    if tc_match:
        tc = tc_match.group(1).strip()

    if sc_match:
        sc = sc_match.group(1).strip()

    return tc, sc


# ---------------------------------------------------------
# SOLUTION SECTIONS
# ---------------------------------------------------------

def extract_solution_sections(soup):

    article = get_article_container(soup)

    text = article.get_text("\n", strip=True)

    lines = [x.strip() for x in text.split("\n") if x.strip()]

    brute_force = []
    optimized = []
    explanation = []

    current = None

    for line in lines:

        lower = line.lower()

        # brute force
        if re.search(r"brute|naive", lower):
            current = "brute"
            continue

        # optimized
        if re.search(r"optimal|optimized|efficient", lower):
            current = "optimized"
            continue

        # explanation
        if re.search(r"approach|algorithm|intuition", lower):
            current = "explanation"
            continue

        if current == "brute":
            brute_force.append(line)

        elif current == "optimized":
            optimized.append(line)

        elif current == "explanation":
            explanation.append(line)

    return {
        "brute_force": clean_text(
            "\n".join(brute_force)
        ),
        "optimized_approach": clean_text(
            "\n".join(optimized)
        ),
        "explanation": clean_text(
            "\n".join(explanation)
        ),
    }


# ---------------------------------------------------------
# SCRAPE SINGLE PROBLEM
# ---------------------------------------------------------

async def scrape_problem(page, url):

    global visited_problem_urls

    if url in visited_problem_urls:
        return None

    visited_problem_urls.add(url)

    success = await safe_goto(page, url)

    if not success:
        return None

    html = await page.content()

    soup = BeautifulSoup(html, "lxml")

    article = get_article_container(soup)

    full_text = article.get_text("\n", strip=True)

    problem_id = str(uuid.uuid4())[:8]

    title = extract_title(soup)

    tags = extract_tags(soup)

    difficulty = extract_difficulty(soup)

    statement = extract_problem_statement(soup)

    constraints = extract_constraints(soup)

    examples = extract_examples(soup)

    code = extract_code_blocks(soup)

    sections = extract_solution_sections(soup)

    tc, sc = extract_complexities(full_text)

    # QUESTIONS CSV ROW
    question = {
        "problem_id": problem_id,
        "url": url,
        "title": title,
        "statement": statement,
        "constraints": constraints,
        "examples": str(examples),
        "tags": str(tags),
        "difficulty": difficulty,
    }

    # SOLUTIONS CSV ROW
    solution = {
        "problem_id": problem_id,
        "title": title,
        "brute_force_solution": sections["brute_force"],
        "optimized_approach": sections["optimized_approach"],
        "explanation": sections["explanation"],
        "time_complexity": tc,
        "space_complexity": sc,
        "cpp_code": code["cpp"],
        "java_code": code["java"],
        "python_code": code["python"],
        "javascript_code": code["javascript"],
    }

    return question, solution


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

async def main():

    all_questions = []
    all_solutions = []

    async with async_playwright() as pw:

        browser = await pw.firefox.launch(
            headless=False,
            slow_mo=150
)

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={
                "width": 1366,
                "height": 768
            },
            locale="en-US",
            java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "DNT": "1",
            }
        )

        page = await context.new_page()

        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        """)

        # -------------------------------------------------
        # STEP 1: COLLECT LINKS
        # -------------------------------------------------

        print("\n[STEP 1] Collecting links...\n")

        problem_links = await collect_problem_links(
            page,
            SEED_URLS
        )

        print(f"\n[FOUND] {len(problem_links)} problem links\n")

        # -------------------------------------------------
        # STEP 2: SCRAPE EACH PROBLEM
        # -------------------------------------------------

        print("\n[STEP 2] Scraping problems...\n")

        for idx, link in enumerate(problem_links):

            print(
                f"\n[{idx + 1}/{len(problem_links)}]"
            )

            result = await scrape_problem(
                page,
                link
            )

            if result:

                question, solution = result

                all_questions.append(question)
                all_solutions.append(solution)

                print(
                    f"[SUCCESS] {question['title']}"
                )

            else:
                print("[FAILED]")

        await browser.close()

    # -----------------------------------------------------
    # STEP 3: EXPORT CSV
    # -----------------------------------------------------

    print("\n[STEP 3] Saving CSV files...\n")

    questions_df = pd.DataFrame(all_questions)

    solutions_df = pd.DataFrame(all_solutions)

    questions_df.to_csv(
        "questions.csv",
        index=False,
        encoding="utf-8-sig"
    )

    solutions_df.to_csv(
        "solutions.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nDONE!")
    print(f"Questions: {len(all_questions)}")
    print(f"Solutions: {len(all_solutions)}")
    print("Generated:")
    print(" - questions.csv")
    print(" - solutions.csv")


# ---------------------------------------------------------
# ENTRY
# ---------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())