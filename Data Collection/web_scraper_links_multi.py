# gfg_link_scraper.py
# Scrapes all problem links from a GFG DSA topic page
# Output: links.csv (one link per row)

import asyncio
import csv
import re
import os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

INPUT_CSV  = r"D:\Programming\End-to-End-AI-Powered-DSA-RAG-Engine-AskDSA\Datasets\Dataset with links\web_links.csv"
OUTPUT_DIR = r"D:\Programming\End-to-End-AI-Powered-DSA-RAG-Engine-AskDSA\Datasets\Dataset with links"

async def scrape_links(page, url: str) -> list[str]:
    print(f"  Loading: {url}")
    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    links = []
    html_chunk = soup.find("div", class_="html-chunk")

    if html_chunk:
        for ul in html_chunk.find_all("ul"):
            for li in ul.find_all("li"):
                a_tag = li.find("a", href=True)
                if a_tag:
                    href = a_tag["href"].strip()
                    if href.startswith("https://www.geeksforgeeks.org"):
                        links.append(href)

    return links

async def main():
    # Read all (name, url) pairs from the input CSV
    rows = []
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header row (Name_of_link, links)
        for row in reader:
            if len(row) >= 2:
                name = row[0].strip()
                url  = row[1].strip()
                rows.append((name, url))

    print(f"Found {len(rows)} URLs to process\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        for idx, (name, url) in enumerate(rows, start=1):
            print(f"[{idx}/{len(rows)}] {name}")

            try:
                links = await scrape_links(page, url)
            except Exception as e:
                print(f"  [ERROR] {name}: {e}")
                links = []

            # Output file named after the first column e.g. links_array_top_50.csv
            output_file = os.path.join(OUTPUT_DIR, f"links_{name}.csv")

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["link"])
                for link in links:
                    writer.writerow([link])

            print(f"  Saved {len(links)} links → links_{name}.csv")

            # Polite delay between pages
            await asyncio.sleep(2)

        await browser.close()

    print(f"\nAll done! {len(rows)} files saved to:\n{OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())