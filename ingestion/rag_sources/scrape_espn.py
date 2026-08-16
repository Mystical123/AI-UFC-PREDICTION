"""Scrape ESPN for analyst articles about each fight in our scraped fight cards,
saving one JSON file per fight to data/raw/espn/<event_slug>/.

ESPN sits behind an AWS WAF JS challenge (same category of problem as UFCStats'
Anubis check), so plain requests can't reach it -- Playwright is required for
every page. Unlike UFCStats, ESPN's page never reaches Playwright's
"networkidle" state (constant ad/analytics polling in the background), so we
use wait_until="domcontentloaded" + a short fixed settle wait instead -- timed
empirically: real content (story links) is already present ~500ms after
domcontentloaded, so 1500ms gives comfortable margin without the multi-second
waits networkidle would have forced.
"""
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.espn.com"
FIGHT_CARDS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "fight_cards"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "espn"
MAX_ARTICLES_PER_FIGHT = 8
SETTLE_MS = 1500


def _normalize(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", _normalize(name)).strip("-")


def collect_fights():
    fights = []
    for path in sorted(FIGHT_CARDS_DIR.glob("*.json")):
        event = json.loads(path.read_text())
        event_slug = path.stem
        for fight in event["fights"]:
            fights.append(
                {
                    "event_slug": event_slug,
                    "event_name": event["event_name"],
                    "fighter_red": fight["fighter_red"],
                    "fighter_blue": fight["fighter_blue"],
                    "weight_class": fight["weight_class"],
                }
            )
    return fights


def _goto(page, url):
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(SETTLE_MS)
    return BeautifulSoup(page.content(), "html.parser")


def find_fighter_url(page, name):
    soup = _goto(page, f"{BASE_URL}/search/results?q={quote(name)}")
    link = soup.select_one("a[href*='/mma/fighter/_/id/']")
    if not link or not link.get("href"):
        return None
    href = link["href"]
    return href if href.startswith("http") else BASE_URL + href


def fetch_fighter_news_links(page, fighter_url):
    m = re.search(r"/id/(\d+)/([^/?#]+)", fighter_url)
    if not m:
        return []
    fighter_id, slug = m.group(1), m.group(2)
    soup = _goto(page, f"{BASE_URL}/mma/fighter/news/_/id/{fighter_id}/{slug}")

    seen = set()
    links = []
    for a in soup.select("a[href*='/mma/story/_/id/']"):
        href = a["href"]
        href = href if href.startswith("http") else BASE_URL + href
        text = a.get_text(strip=True)
        if not text or href in seen:
            continue
        seen.add(href)
        links.append({"title": text, "url": href})
    return links


def scrape_article(page, url):
    soup = _goto(page, url)

    title_el = soup.select_one(".article-header h1")
    author_el = soup.select_one(".article-meta .author")
    author = next(author_el.stripped_strings, None) if author_el else None
    body_el = soup.select_one(".article-body")
    paragraphs = body_el.select("p") if body_el else []
    body_text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)

    return {
        "title": title_el.get_text(strip=True) if title_el else None,
        "author": author,
        "body_text": body_text or None,
    }


def matches_fight(title, fighter_red, fighter_blue):
    title_norm = _normalize(title)
    red_key = _normalize(fighter_red.split()[-1])
    blue_key = _normalize(fighter_blue.split()[-1])
    return red_key in title_norm and blue_key in title_norm


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fights = collect_fights()
    print(f"Searching ESPN for {len(fights)} fights")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for fight in fights:
            event_dir = OUTPUT_DIR / fight["event_slug"]
            event_dir.mkdir(exist_ok=True)
            out_path = event_dir / f"{slugify(fight['fighter_red'])}-vs-{slugify(fight['fighter_blue'])}.json"
            if out_path.exists():
                continue

            candidate_links = []
            for name in (fight["fighter_red"], fight["fighter_blue"]):
                fighter_url = find_fighter_url(page, name)
                if fighter_url:
                    candidate_links += fetch_fighter_news_links(page, fighter_url)

            seen_urls = set()
            matched = []
            for item in candidate_links:
                if item["url"] in seen_urls:
                    continue
                if not matches_fight(item["title"], fight["fighter_red"], fight["fighter_blue"]):
                    continue
                seen_urls.add(item["url"])
                matched.append(item)
                if len(matched) >= MAX_ARTICLES_PER_FIGHT:
                    break

            articles = []
            for item in matched:
                detail = scrape_article(page, item["url"])
                articles.append({**item, **detail})
                time.sleep(1)

            result = {**fight, "articles": articles}
            out_path.write_text(json.dumps(result, indent=2))
            print(
                f"Saved {fight['fighter_red']} vs {fight['fighter_blue']} "
                f"({len(articles)} articles) -> {out_path}"
            )

        browser.close()


if __name__ == "__main__":
    main()
