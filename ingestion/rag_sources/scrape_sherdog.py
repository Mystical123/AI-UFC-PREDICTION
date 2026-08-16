"""Scrape Sherdog.com for analyst/news articles about each fight in our scraped
fight cards, saving one JSON file per fight to data/raw/sherdog/<event_slug>/.

Sherdog's own site search (/search.php) doesn't actually filter anything -- it
returns byte-identical content to the homepage regardless of query, and its
per-fighter "related news" module is a generic latest-news widget mislabeled
with the fighter's name, not real per-fighter tagging (both confirmed by
diffing responses before writing this). The one thing that IS real is the
/tag/ufc listing, so instead of searching per-fight, we pull a pool of recent
UFC articles once and match them against each fight by fighter last name.
"""
import json
import re
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.sherdog.com"
FIGHT_CARDS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "fight_cards"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "sherdog"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TAG_PAGES_TO_FETCH = 5  # /tag/ufc + /tag/ufc/list/2..5 -> recent-article pool


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


def fetch_recent_ufc_articles():
    articles = []
    seen_urls = set()
    for page_num in range(1, TAG_PAGES_TO_FETCH + 1):
        url = f"{BASE_URL}/tag/ufc" if page_num == 1 else f"{BASE_URL}/tag/ufc/list/{page_num}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for module in soup.select(".left-article-module"):
            link = module.select_one("a.title")
            if not link or not link.get("href"):
                continue
            href = link["href"]
            article_url = href if href.startswith("http") else BASE_URL + href
            if article_url in seen_urls:
                continue
            seen_urls.add(article_url)

            date_el = module.select_one(".date")
            author_el = module.select_one(".authors a")
            articles.append(
                {
                    "title": link.get_text(strip=True),
                    "url": article_url,
                    "author": author_el.get_text(strip=True) if author_el else None,
                    "date_timestamp": int(date_el["data-date"])
                    if date_el and date_el.get("data-date")
                    else None,
                }
            )
        time.sleep(1)
    return articles


def scrape_article_body(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    body_el = soup.select_one(".content.body_content")
    if not body_el:
        return None
    for tag in body_el.select("script, .a2a_kit"):
        tag.decompose()
    for ad_div in body_el.find_all("div", id=lambda x: x and x.startswith("adViAi")):
        ad_div.decompose()

    text = body_el.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)


def matches_fight(article_title, fighter_red, fighter_blue):
    title_norm = _normalize(article_title)
    red_key = _normalize(fighter_red.split()[-1])
    blue_key = _normalize(fighter_blue.split()[-1])
    return red_key in title_norm and blue_key in title_norm


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fights = collect_fights()

    print("Fetching recent UFC news pool from Sherdog...")
    articles_pool = fetch_recent_ufc_articles()
    print(f"Pool has {len(articles_pool)} recent articles")

    for fight in fights:
        event_dir = OUTPUT_DIR / fight["event_slug"]
        event_dir.mkdir(exist_ok=True)
        out_path = event_dir / f"{slugify(fight['fighter_red'])}-vs-{slugify(fight['fighter_blue'])}.json"
        if out_path.exists():
            continue

        matched = [
            a for a in articles_pool if matches_fight(a["title"], fight["fighter_red"], fight["fighter_blue"])
        ]
        articles = []
        for a in matched:
            body = scrape_article_body(a["url"])
            articles.append({**a, "body_text": body})
            time.sleep(1)

        result = {**fight, "articles": articles}
        out_path.write_text(json.dumps(result, indent=2))
        print(
            f"Saved {fight['fighter_red']} vs {fight['fighter_blue']} "
            f"({len(articles)} articles) -> {out_path}"
        )


if __name__ == "__main__":
    main()
