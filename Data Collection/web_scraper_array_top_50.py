# gfg_link_scraper.py
# Scrapes all problem links from a GFG DSA topic page
# Output: links.csv (one link per row)

import asyncio
import csv
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# TARGET_URL = "https://www.geeksforgeeks.org/dsa/top-50-array-coding-problems-for-interviews/"
TARGET_URL = "https://www.geeksforgeeks.org/dsa/array-data-structure-guide/"
OUTPUT_FILE = r"D:\Programming\End-to-End-AI-Powered-DSA-RAG-Engine-AskDSA\Datasets\Dataset with links\links_array_data_structure.csv"

async def scrape_links():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        print(f"Loading: {TARGET_URL}")
        await page.goto(TARGET_URL, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(3)  # let JS render fully

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Target exactly: div.html-chunk > ul > li > a
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

    # Save to CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["link"])          # header
        for link in links:
            writer.writerow([link])

    print(f"Done! {len(links)} links saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(scrape_links())