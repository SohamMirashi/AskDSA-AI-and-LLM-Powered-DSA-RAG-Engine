# gfg_link_scraper.py
# Scrapes all problem links from a GFG DSA topic page
# Output: links.csv (one link per row)

import asyncio
import csv
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

TARGET_URL = r"https://www.geeksforgeeks.org/dsa/top-50-problems-on-hash-data-structure-asked-in-sde-interviews/"
OUTPUT_FILE = r"D:\Programming\End-to-End-AI-Powered-DSA-RAG-Engine-AskDSA\links_greedy_top_20.csv"

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

    # Check the HTML structure before running the code
    links = []
    html_chunk = soup.find("div", class_="html-chunk")

    if html_chunk:
        # ── Structure 1: div.html-chunk > ol > li > a
        for ol in html_chunk.find_all("ol"):
            for li in ol.find_all("li"):
                a_tag = li.find("a", href=True)
                if a_tag:
                    href = a_tag["href"].strip()
                    if href.startswith("https://www.geeksforgeeks.org"):
                        links.append(href)

        # ── Structure 2: div.html-chunk > ul > li > a
        for ul in html_chunk.find_all("ul"):
            for li in ul.find_all("li"):
                a_tag = li.find("a", href=True)
                if a_tag:
                    href = a_tag["href"].strip()
                    if href.startswith("https://www.geeksforgeeks.org"):
                        links.append(href)

        # ── Structure 3: table > tbody > tr > td > a 
        for table in html_chunk.find_all("table"):
            for tr in table.find_all("tr"):
                for td in tr.find_all("td"):
                    a_tag = td.find("a", href=True)
                    if a_tag:
                        href = a_tag["href"].strip()
                        if href.startswith("https://www.geeksforgeeks.org") and href not in links:
                            links.append(href)

    # Save to CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["link"]) # header
        for link in links:
            writer.writerow([link])

    print(f"Done! {len(links)} links saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(scrape_links())