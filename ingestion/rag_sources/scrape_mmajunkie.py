"""Scrape MMA Junkie for analyst articles about each fight in our scraped fight
cards, saving one JSON file per fight to data/raw/mmajunkie/<event_slug>/.

MMA Junkie (a USA Today/Gannett site) renders its search results AND article
bodies inside Shadow DOM -- confirmed by comparing plain `requests` output
(no article content at all) against Playwright's page.content() (still no
content -- outerHTML doesn't serialize shadow roots) against a JS walk of
document + all shadowRoots (finds everything). So unlike Sherdog, this needs
Playwright for every page, not just discovery.
"""
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

BASE_URL = "https://mmajunkie.usatoday.com"
FIGHT_CARDS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "fight_cards"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "mmajunkie"
MAX_ARTICLES_PER_FIGHT = 8

# Real content (search results, article text) lives inside Shadow DOM, which
# Playwright's page.content()/outerHTML doesn't serialize -- these walk every
# shadow root via JS to find it, same as a real browser rendering the page.
SHADOW_LINK_WALK_JS = """
() => {
    function walk(root, results) {
        root.querySelectorAll('a[href]').forEach(a => {
            results.push([a.href, a.textContent.trim()]);
        });
        root.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) walk(el.shadowRoot, results);
        });
        return results;
    }
    return walk(document, []);
}
"""
SHADOW_CLASS_WALK_JS = """
(cls) => {
    function findByClass(root, cls, results) {
        root.querySelectorAll('.' + cls).forEach(el => results.push(el.textContent.trim()));
        root.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) findByClass(el.shadowRoot, cls, results);
        });
        return results;
    }
    return findByClass(document, cls, []);
}
"""

# Real articles live at /<story|videos|picture-gallery>/sports/ufc/YYYY/MM/DD/...
# -- this also filters out nav/footer links (Videos, Schedule, Careers, etc.)
# which don't match the dated path.
ARTICLE_URL_PATTERN = re.compile(r"/(story|videos|picture-gallery)/sports/ufc/\d{4}/\d{2}/\d{2}/")
VIDEO_PLAYER_BOILERPLATE = re.compile(
    r"^(Play\s*Unmute\s*)?(\d{1,2}:\d{2}\s*/\s*\d{1,2}:\d{2}\s*)?(Full\s*screen\s*)?(Keep\s*Watching\s*)?",
    re.IGNORECASE,
)


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


def search_articles(page, fighter_red, fighter_blue):
    query = f"{fighter_red} {fighter_blue}"
    page.goto(f"{BASE_URL}/search/?q={quote(query)}", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    links = page.evaluate(SHADOW_LINK_WALK_JS)

    red_key = _normalize(fighter_red.split()[-1])
    blue_key = _normalize(fighter_blue.split()[-1])

    seen = set()
    matched = []
    for href, text in links:
        if href in seen or not text or not ARTICLE_URL_PATTERN.search(href):
            continue
        title_norm = _normalize(text)
        if red_key not in title_norm or blue_key not in title_norm:
            continue
        seen.add(href)
        matched.append({"title": text, "url": href})
        if len(matched) >= MAX_ARTICLES_PER_FIGHT:
            break
    return matched


def scrape_article(page, url):
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    headline = page.evaluate(SHADOW_CLASS_WALK_JS, "gnt_ar_hl")
    byline = page.evaluate(SHADOW_CLASS_WALK_JS, "gnt_ar_by")
    body_parts = page.evaluate(SHADOW_CLASS_WALK_JS, "gnt_ar_b")

    body_text = " ".join(body_parts)
    body_text = VIDEO_PLAYER_BOILERPLATE.sub("", body_text)
    body_text = re.sub(r"\s+", " ", body_text).strip()

    return {
        "title": headline[0] if headline else None,
        "author": byline[0] if byline else None,
        "body_text": body_text or None,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fights = collect_fights()
    print(f"Searching MMA Junkie for {len(fights)} fights")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for fight in fights:
            event_dir = OUTPUT_DIR / fight["event_slug"]
            event_dir.mkdir(exist_ok=True)
            out_path = event_dir / f"{slugify(fight['fighter_red'])}-vs-{slugify(fight['fighter_blue'])}.json"
            if out_path.exists():
                continue

            found = search_articles(page, fight["fighter_red"], fight["fighter_blue"])
            articles = []
            for item in found:
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
