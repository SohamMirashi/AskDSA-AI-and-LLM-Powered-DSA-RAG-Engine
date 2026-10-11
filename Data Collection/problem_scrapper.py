import csv
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# MANUAL TARGET URL
# ------------------------------------------------------------
# Put any GFG DSA problem URL here.
#
# Example:
# TARGET_URL = "https://www.geeksforgeeks.org/dsa/print-alternate-elements-of-an-array/"
#
# If TARGET_URL is empty, the script will process all CSV files
# inside INPUT_DIR.
# ------------------------------------------------------------

TARGET_URL = "https://www.geeksforgeeks.org/dsa/print-alternate-elements-of-an-array/"


# ------------------------------------------------------------
# PROJECT DIRECTORIES
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_DIR = BASE_DIR / "Datasets" / "Dataset with links"

HTML_DIR = BASE_DIR / "saved_html"

OUTPUT_FILE = BASE_DIR / "scraped_gfg_problems.csv"


# ------------------------------------------------------------
# SCRAPER SETTINGS
# ------------------------------------------------------------

MAX_APPROACHES = 4

REQUEST_TIMEOUT = 20

MAX_RETRIES = 3

# Delay between requests when processing multiple URLs.
REQUEST_DELAY = 2


# ------------------------------------------------------------
# SUPPORTED LANGUAGES
# ------------------------------------------------------------
# These are the languages we currently want in the CSV.
#
# The parser detects which languages actually exist on the
# GFG page. Missing languages are simply left empty.
# ------------------------------------------------------------

LANGUAGES = {
    "cpp": "cpp",
    "java": "java",
    "python": "python",
    "c": "c",
    "csharp": "csharp",
    "javascript": "javascript",
}


# Some pages may use slightly different names for languages.
LANGUAGE_ALIASES = {
    "cpp": "cpp",
    "c++": "cpp",
    "cplusplus": "cpp",

    "java": "java",

    "python": "python",
    "python3": "python",

    "c": "c",

    "c#": "csharp",
    "csharp": "csharp",
    "cs": "csharp",

    "javascript": "javascript",
    "js": "javascript",
}


# ------------------------------------------------------------
# CREATE DIRECTORIES
# ------------------------------------------------------------

HTML_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CSV COLUMNS
# ============================================================

COLUMNS = [
    "source_url",
    "source_csv",
    "source_row",
    "problem_title",
    "problem_statement",
    "examples",
    "constraints",
    "difficulty",
]


for approach_number in range(1, MAX_APPROACHES + 1):

    COLUMNS.extend([
        f"approach_{approach_number}_heading",
        f"approach_{approach_number}_explanation",

        # Keep these empty for now.
        f"approach_{approach_number}_tc",
        f"approach_{approach_number}_sc",

        f"approach_{approach_number}_cpp",
        f"approach_{approach_number}_java",
        f"approach_{approach_number}_python",
        f"approach_{approach_number}_c",
        f"approach_{approach_number}_csharp",
        f"approach_{approach_number}_javascript",
    ])


COLUMNS.extend([
    "scrape_status",
    "scrape_error",
])


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(text):
    """
    Clean normal article text.

    Keeps line breaks useful for:
        examples
        constraints
        explanations
    """

    if not text:
        return ""

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def normalize_text(text):
    """
    Normalize text for comparisons.
    """

    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip().lower()


# ============================================================
# URL / FILE HELPERS
# ============================================================

def get_url_slug(url):
    """
    Convert:

    https://www.geeksforgeeks.org/dsa/print-alternate-elements-of-an-array/

    into:

    print-alternate-elements-of-an-array
    """

    parsed = urlparse(url)

    path = parsed.path.rstrip("/")

    slug = path.split("/")[-1]

    return slug


def get_html_path(url):
    """
    Return local HTML path for a URL.
    """

    slug = get_url_slug(url)

    if not slug:
        raise ValueError(
            "Could not determine page slug from URL."
        )

    return HTML_DIR / f"{slug}.html"


# ============================================================
# DOWNLOAD HTML
# ============================================================

def download_html(url):
    """
    Download the GFG page.

    Includes:
        - browser-like headers
        - timeout
        - retries
        - delay between retries

    Returns:
        HTML string
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,"
            "*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(
                f"  Downloading "
                f"(attempt {attempt}/{MAX_RETRIES})..."
            )

            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            if not response.text.strip():
                raise ValueError(
                    "Server returned an empty HTML page."
                )

            return response.text

        except Exception as error:

            last_error = error

            print(
                f"  Request failed: {type(error).__name__}: "
                f"{error}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(REQUEST_DELAY)

    raise RuntimeError(
        f"Could not download page after "
        f"{MAX_RETRIES} attempts: {last_error}"
    )


def get_soup(url):
    """
    Get BeautifulSoup object.

    First checks whether the page has already been saved
    locally.

    If it exists, the saved copy is used.

    Otherwise, the page is downloaded.
    """

    html_path = get_html_path(url)

    # --------------------------------------------------------
    # USE EXISTING HTML
    # --------------------------------------------------------

    if html_path.exists():

        print(
            f"  Using existing HTML: "
            f"{html_path.name}"
        )

        try:

            html = html_path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            html = html_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

    # --------------------------------------------------------
    # DOWNLOAD HTML
    # --------------------------------------------------------

    else:

        html = download_html(url)

        try:

            html_path.write_text(
                html,
                encoding="utf-8",
            )

            print(
                f"  Saved HTML: {html_path}"
            )

        except Exception as error:

            print(
                f"  Warning: Could not save HTML: "
                f"{error}"
            )

    return BeautifulSoup(
        html,
        "html.parser"
    )


# ============================================================
# ARTICLE DETECTION
# ============================================================

def find_article(soup):
    """
    Locate the main GFG article.

    GFG uses generated class names, so we intentionally use
    partial class matching.

    Multiple fallbacks are provided.
    """

    selectors = [

        # Seen in the supplied DOM screenshots.
        "div[class*='article--viewer_content']",

        "div[class*='MainArticleContent_articleMainContent']",

        "div[class*='articleMainContent']",

        "article",

        "main",

        "div.a-wrapper",
    ]

    for selector in selectors:

        article = soup.select_one(selector)

        if article is None:
            continue

        # Make sure this is actually an article and not
        # some unrelated container.
        if article.find(
            ["h1", "h2", "h3", "h4"]
        ):

            return article

    raise ValueError(
        "ARTICLE_PARSER_NOT_FOUND: "
        "Could not find the main GFG article."
    )


# ============================================================
# TITLE
# ============================================================

def extract_title(soup, article):
    """
    Extract problem title.
    """

    selectors = [

        # Seen in the screenshots.
        "div[class*='ArticleHeader_article-title'] h1",

        "h1",
    ]

    for selector in selectors:

        element = soup.select_one(selector)

        if element:

            title = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if title:
                return title

    # Fallback to <title>
    if soup.title:

        title = clean_text(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

        if title:
            return title

    return ""


# ============================================================
# PROBLEM STATEMENT
# ============================================================

def extract_problem_statement(article):
    """
    Try to obtain the initial problem description.

    We intentionally stop before solution approaches.
    """

    paragraphs = article.find_all("p")

    collected = []

    for paragraph in paragraphs:

        text = clean_text(
            paragraph.get_text(
                "\n",
                strip=True
            )
        )

        if not text:
            continue

        normalized = normalize_text(text)

        # Ignore tiny decorative text.
        if len(text) < 20:
            continue

        # Stop once solution approaches begin.
        if (
            "naive approach" in normalized
            or "brute force" in normalized
            or "better approach" in normalized
            or "expected approach" in normalized
            or "optimal approach" in normalized
        ):
            break

        collected.append(text)

        # Usually the actual problem statement is contained
        # in the first few meaningful paragraphs.
        if len(collected) >= 3:
            break

    return "\n".join(collected)


# ============================================================
# EXAMPLES / CONSTRAINTS
# ============================================================

def find_heading(article, target):
    """
    Find a heading whose normalized text matches target.
    """

    target = normalize_text(target)

    for heading in article.find_all(
        ["h2", "h3", "h4"]
    ):

        heading_text = normalize_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if heading_text == target:
            return heading

    return None


def extract_section_after_heading(
    article,
    target
):
    """
    Extract content after:

        Examples

    or:

        Constraints

    until the next major heading.
    """

    heading = find_heading(
        article,
        target
    )

    if heading is None:
        return ""

    result = []

    for element in heading.find_all_next():

        # Stop at next major heading.
        if element.name in {
            "h2",
            "h3",
            "h4"
        }:

            break

        if element.name in {
            "script",
            "style",
            "button"
        }:

            continue

        if element.name in {
            "p",
            "li",
            "pre"
        }:

            text = clean_text(
                element.get_text(
                    "\n",
                    strip=True
                )
            )

            if text and text not in result:

                result.append(text)

    return "\n".join(result)


# ============================================================
# DIFFICULTY
# ============================================================

def extract_difficulty(soup):
    """
    Try to find:

        Difficulty: Easy
        Difficulty: Medium
        Difficulty: Hard
    """

    page_text = soup.get_text(
        " ",
        strip=True
    )

    match = re.search(
        r"Difficulty\s*:\s*"
        r"(Easy|Medium|Hard)",
        page_text,
        re.IGNORECASE,
    )

    if match:

        return match.group(1).title()

    return ""


# ============================================================
# APPROACH HEADING DETECTION
# ============================================================

def is_approach_heading(heading):
    """
    Determine whether a heading represents a solution
    approach.

    Examples:

        [Naive Approach] Using Nested Loops
        [Better Approach] Using Running Prefix Sum
        [Expected Approach] Using Queue
        Optimal Approach
    """

    text = normalize_text(
        heading.get_text(
            " ",
            strip=True
        )
    )

    patterns = [

        r"\bnaive approach\b",

        r"\bbrute force\b",

        r"\bbrute-force\b",

        r"\bbetter approach\b",

        r"\bexpected approach\b",

        r"\boptimal approach\b",

        r"\befficient approach\b",

        r"\bapproach\b",
    ]

    for pattern in patterns:

        if re.search(pattern, text):

            return True

    return False


# ============================================================
# FIND APPROACHES
# ============================================================

def find_approach_headings(article):
    """
    Return all headings that appear to represent solution
    approaches.
    """

    headings = []

    for heading in article.find_all(
        ["h2", "h3", "h4"]
    ):

        if is_approach_heading(heading):

            headings.append(heading)

    return headings


# ============================================================
# LANGUAGE NORMALIZATION
# ============================================================

def normalize_language(language):
    """
    Convert GFG language names into our standard names.
    """

    if not language:
        return None

    language = normalize_text(language)

    # Remove things such as:
    # "c++ solution"
    # "python3"
    language = language.replace(
        "solution",
        ""
    ).strip()

    if language in LANGUAGE_ALIASES:

        return LANGUAGE_ALIASES[language]

    return None


# ============================================================
# EXTRACT CODE FROM AN APPROACH
# ============================================================

def extract_codes_from_section(
    section_elements
):
    """
    Extract available programming language implementations.

    GFG's structure visible in your screenshots includes:

        <gfg-tabs>

            <gfg-tab ...>
                C++
            </gfg-tab>

            <gfg-panel
                data-code-lang="cpp"
                ...
            >

        </gfg-tabs>

    Therefore, data-code-lang is preferred.

    Fallbacks are included for pages where that attribute
    is unavailable.
    """

    codes = {
        "cpp": "",
        "java": "",
        "python": "",
        "c": "",
        "csharp": "",
        "javascript": "",
    }

    # --------------------------------------------------------
    # METHOD 1
    # data-code-lang
    # --------------------------------------------------------

    for element in section_elements:

        if not hasattr(element, "find_all"):
            continue

        panels = element.find_all(
            "gfg-panel"
        )

        for panel in panels:

            language = panel.get(
                "data-code-lang"
            )

            language = normalize_language(
                language
            )

            if not language:
                continue

            if language not in codes:
                continue

            # Look for actual <code>.
            code_element = panel.find(
                "code"
            )

            if code_element is None:

                # Sometimes code can be inside
                # highlighted/pre structures.
                code_element = panel.find(
                    "pre"
                )

            if code_element is None:
                continue

            code = code_element.get_text(
                "",
                strip=False
            ).strip()

            if code and not codes[language]:

                codes[language] = code

    # --------------------------------------------------------
    # METHOD 2
    # Fallback using code class
    # --------------------------------------------------------

    if not any(codes.values()):

        for element in section_elements:

            if not hasattr(element, "find_all"):
                continue

            code_elements = element.find_all(
                "code"
            )

            for code_element in code_elements:

                classes = code_element.get(
                    "class",
                    []
                )

                class_text = " ".join(
                    classes
                ).lower()

                language = None

                if (
                    "language-cpp"
                    in class_text
                    or "language-c++"
                    in class_text
                ):

                    language = "cpp"

                elif (
                    "language-java"
                    in class_text
                ):

                    language = "java"

                elif (
                    "language-python"
                    in class_text
                ):

                    language = "python"

                elif (
                    "language-c"
                    in class_text
                ):

                    language = "c"

                elif (
                    "language-csharp"
                    in class_text
                    or "language-c#" in class_text
                ):

                    language = "csharp"

                elif (
                    "language-javascript"
                    in class_text
                    or "language-js"
                    in class_text
                ):

                    language = "javascript"

                if not language:
                    continue

                code = code_element.get_text(
                    "",
                    strip=False
                ).strip()

                if (
                    code
                    and not codes[language]
                ):

                    codes[language] = code

    return codes


# ============================================================
# EXTRACT APPROACH CONTENT
# ============================================================

def get_elements_between(
    start_heading,
    end_heading
):
    """
    Get DOM elements between two headings.

    The end heading itself is not included.
    """

    elements = []

    current = start_heading

    while current:

        current = current.find_next()

        if current is None:
            break

        if current == end_heading:
            break

        elements.append(current)

    return elements


def extract_explanation(
    section_elements
):
    """
    Extract explanation text from an approach.

    Code blocks and GFG code tabs are excluded.
    """

    parts = []

    for element in section_elements:

        # We only care about paragraph/list content.
        if element.name not in {
            "p",
            "li",
        }:

            continue

        text = clean_text(
            element.get_text(
                "\n",
                strip=True
            )
        )

        if not text:
            continue

        # Avoid duplicating nested list text.
        if text in parts:
            continue

        parts.append(text)

    return "\n".join(parts)


# ============================================================
# EXTRACT ALL APPROACHES
# ============================================================

def extract_approaches(article):
    """
    Extract maximum four solution approaches.
    """

    approach_headings = (
        find_approach_headings(article)
    )

    approaches = []

    for index, heading in enumerate(
        approach_headings
    ):

        if len(approaches) >= MAX_APPROACHES:
            break

        # ----------------------------------------------------
        # Find next approach heading
        # ----------------------------------------------------

        next_heading = None

        if index + 1 < len(
            approach_headings
        ):

            next_heading = (
                approach_headings[index + 1]
            )

        # ----------------------------------------------------
        # Get content between headings
        # ----------------------------------------------------

        section_elements = (
            get_elements_between(
                heading,
                next_heading
            )
        )

        # ----------------------------------------------------
        # Extract heading
        # ----------------------------------------------------

        heading_text = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

        # ----------------------------------------------------
        # Extract explanation
        # ----------------------------------------------------

        explanation = extract_explanation(
            section_elements
        )

        # ----------------------------------------------------
        # Extract code
        # ----------------------------------------------------

        codes = extract_codes_from_section(
            section_elements
        )

        # ----------------------------------------------------
        # Don't save completely empty sections
        # ----------------------------------------------------

        if (
            not explanation
            and not any(codes.values())
        ):

            continue

        approaches.append({
            "heading": heading_text,
            "explanation": explanation,

            # Deliberately empty.
            "tc": "",
            "sc": "",

            "cpp": codes["cpp"],
            "java": codes["java"],
            "python": codes["python"],
            "c": codes["c"],
            "csharp": codes["csharp"],
            "javascript": codes["javascript"],
        })

    return approaches


# ============================================================
# SCRAPE ONE PROBLEM
# ============================================================

def scrape_problem(
    url,
    source_csv="",
    source_row=""
):
    """
    Scrape a single problem.

    Returns a dictionary matching the CSV schema.
    """

    result = {
        column: ""
        for column in COLUMNS
    }

    result["source_url"] = url

    result["source_csv"] = source_csv

    result["source_row"] = source_row

    try:

        print("\n==========================================")
        print("Processing:")
        print(url)
        print("==========================================")

        # ----------------------------------------------------
        # Get page
        # ----------------------------------------------------

        soup = get_soup(url)

        # ----------------------------------------------------
        # Find article
        # ----------------------------------------------------

        article = find_article(
            soup
        )

        # ----------------------------------------------------
        # Problem title
        # ----------------------------------------------------

        result["problem_title"] = (
            extract_title(
                soup,
                article
            )
        )

        # ----------------------------------------------------
        # Problem statement
        # ----------------------------------------------------

        result["problem_statement"] = (
            extract_problem_statement(
                article
            )
        )

        # ----------------------------------------------------
        # Examples
        # ----------------------------------------------------

        result["examples"] = (
            extract_section_after_heading(
                article,
                "examples"
            )
        )

        # ----------------------------------------------------
        # Constraints
        # ----------------------------------------------------

        result["constraints"] = (
            extract_section_after_heading(
                article,
                "constraints"
            )
        )

        # ----------------------------------------------------
        # Difficulty
        # ----------------------------------------------------

        result["difficulty"] = (
            extract_difficulty(
                soup
            )
        )

        # ----------------------------------------------------
        # Approaches
        # ----------------------------------------------------

        approaches = extract_approaches(
            article
        )

        # ----------------------------------------------------
        # Put approaches into CSV
        # ----------------------------------------------------

        for number, approach in enumerate(
            approaches[:MAX_APPROACHES],
            start=1
        ):

            result[
                f"approach_{number}_heading"
            ] = approach["heading"]

            result[
                f"approach_{number}_explanation"
            ] = approach["explanation"]

            # TC / SC intentionally remain empty.
            result[
                f"approach_{number}_tc"
            ] = ""

            result[
                f"approach_{number}_sc"
            ] = ""

            # ------------------------------------------------
            # Languages
            # ------------------------------------------------

            result[
                f"approach_{number}_cpp"
            ] = approach["cpp"]

            result[
                f"approach_{number}_java"
            ] = approach["java"]

            result[
                f"approach_{number}_python"
            ] = approach["python"]

            result[
                f"approach_{number}_c"
            ] = approach["c"]

            result[
                f"approach_{number}_csharp"
            ] = approach["csharp"]

            result[
                f"approach_{number}_javascript"
            ] = approach["javascript"]

        # ----------------------------------------------------
        # Determine status
        # ----------------------------------------------------

        if not result["problem_title"]:

            result["scrape_status"] = "PARTIAL"

            result["scrape_error"] = (
                "Problem title was not found."
            )

        elif not approaches:

            result["scrape_status"] = "PARTIAL"

            result["scrape_error"] = (
                "Problem found, but no solution "
                "approaches were detected."
            )

        else:

            result["scrape_status"] = "SUCCESS"

            result["scrape_error"] = ""

        return result

    # --------------------------------------------------------
    # KNOWN PARSER ERROR
    # --------------------------------------------------------

    except ValueError as error:

        result["scrape_status"] = "FAILED"

        result["scrape_error"] = str(error)

        return result

    # --------------------------------------------------------
    # ANY OTHER ERROR
    # --------------------------------------------------------

    except Exception as error:

        result["scrape_status"] = "FAILED"

        result["scrape_error"] = (
            f"{type(error).__name__}: {error}"
        )

        return result


# ============================================================
# WRITE ONE RESULT TO CSV
# ============================================================

def write_results(
    results,
    output_file
):
    """
    Write scraped results to CSV.
    """

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=COLUMNS,
            extrasaction="ignore",
        )

        writer.writeheader()

        for result in results:

            writer.writerow(result)


# ============================================================
# FIND URL COLUMN IN INPUT CSV
# ============================================================

def find_url_column(fieldnames):
    """
    Detect common URL column names.
    """

    if not fieldnames:
        return None

    # Exact/common names first.
    for field in fieldnames:

        normalized = normalize_text(
            field
        )

        if normalized in {
            "url",
            "link",
            "problem_url",
            "gfg_link",
        }:

            return field

    # Fallback.
    for field in fieldnames:

        normalized = normalize_text(
            field
        )

        if (
            "url" in normalized
            or "link" in normalized
        ):

            return field

    # If CSV has only one column, assume it
    # contains URLs.
    if len(fieldnames) == 1:

        return fieldnames[0]

    return None


# ============================================================
# BATCH MODE
# ============================================================

def process_csv_files():
    """
    Process every CSV inside INPUT_DIR.
    """

    input_files = sorted(
        INPUT_DIR.glob("*.csv")
    )

    if not input_files:

        print(
            f"No CSV files found in:\n"
            f"{INPUT_DIR}"
        )

        return

    results = []

    total = 0

    success = 0

    partial = 0

    failed = 0

    for csv_file in input_files:

        print(
            f"\n\nReading CSV: "
            f"{csv_file.name}"
        )

        try:

            with csv_file.open(
                "r",
                newline="",
                encoding="utf-8-sig",
            ) as file:

                reader = csv.DictReader(
                    file
                )

                url_column = (
                    find_url_column(
                        reader.fieldnames
                    )
                )

                if not url_column:

                    print(
                        f"Skipping {csv_file.name}: "
                        "No URL column found."
                    )

                    continue

                for row_number, row in enumerate(
                    reader,
                    start=2
                ):

                    url = (
                        row.get(
                            url_column,
                            ""
                        )
                        or ""
                    ).strip()

                    if not url:
                        continue

                    total += 1

                    result = scrape_problem(
                        url=url,
                        source_csv=csv_file.name,
                        source_row=row_number,
                    )

                    results.append(result)

                    status = result[
                        "scrape_status"
                    ]

                    if status == "SUCCESS":
                        success += 1

                    elif status == "PARTIAL":
                        partial += 1

                    else:
                        failed += 1

                    print(
                        f"Status: {status}"
                    )

                    # Be polite when making multiple
                    # network requests.
                    time.sleep(
                        REQUEST_DELAY
                    )

        except Exception as error:

            print(
                f"Could not process "
                f"{csv_file.name}: "
                f"{type(error).__name__}: "
                f"{error}"
            )

    write_results(
        results,
        OUTPUT_FILE
    )

    print("\n==========================================")
    print("BATCH COMPLETE")
    print("==========================================")
    print(f"Total URLs : {total}")
    print(f"Success    : {success}")
    print(f"Partial    : {partial}")
    print(f"Failed     : {failed}")
    print(f"Output     : {OUTPUT_FILE}")


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # MODE 1:
    # TARGET_URL is provided.
    #
    # Only one problem is scraped.
    # --------------------------------------------------------

    if TARGET_URL.strip():

        result = scrape_problem(
            TARGET_URL.strip()
        )

        # For single URL mode, use a separate filename.
        single_output = (
            BASE_DIR
            / "single_gfg_problem.csv"
        )

        write_results(
            [result],
            single_output
        )

        print("\n==========================================")
        print("SINGLE URL COMPLETE")
        print("==========================================")
        print(
            f"Status : "
            f"{result['scrape_status']}"
        )
        print(
            f"Output : "
            f"{single_output}"
        )

        if result["scrape_error"]:

            print(
                f"Error  : "
                f"{result['scrape_error']}"
            )

        return

    # --------------------------------------------------------
    # MODE 2:
    # TARGET_URL is empty.
    #
    # Process all CSV files.
    # --------------------------------------------------------

    process_csv_files()


if __name__ == "__main__":
    main()