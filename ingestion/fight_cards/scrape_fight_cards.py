"""Scrape upcoming UFC event fight cards from ufc.com and save each as local JSON."""
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ufc.com"
EVENTS_URL = f"{BASE_URL}/events"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "fight_cards"

CARD_SEGMENTS = {
    "main-card": "main_card",
    "prelims-card": "prelims",
    "early-prelims": "early_prelims",
}


def get_upcoming_event_urls():
    resp = requests.get(EVENTS_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    urls = []
    for card in soup.select("article.c-card-event--result"):
        link = card.select_one("h3.c-card-event--result__headline a")
        if link and link.get("href"):
            urls.append(BASE_URL + link["href"])
    return urls


def _fighter_name(corner_div):
    if corner_div is None:
        return None
    given = corner_div.select_one(".c-listing-fight__corner-given-name")
    family = corner_div.select_one(".c-listing-fight__corner-family-name")
    if given or family:
        parts = [el.get_text(strip=True) for el in (given, family) if el]
        return " ".join(parts)
    # Some fights (e.g. the main event) render the name as plain text
    # inside the link instead of separate given/family-name spans.
    text = corner_div.get_text(strip=True)
    return text or None


def scrape_event(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title_el = soup.select_one(".field--name-node-title h1")
    event_name = title_el.get_text(strip=True) if title_el else None

    date_el = soup.select_one(".c-hero__headline-suffix")
    date_timestamp = (
        int(date_el["data-timestamp"]) if date_el and date_el.get("data-timestamp") else None
    )
    date_text = date_el.get_text(strip=True) if date_el else None

    venue_el = soup.select_one(".field--name-venue")
    venue = re.sub(r"\s+", " ", venue_el.get_text(strip=True)) if venue_el else None

    fights = []
    for segment_id, segment_label in CARD_SEGMENTS.items():
        container = soup.select_one(f"#{segment_id}")
        if not container:
            continue
        for fight in container.select(".c-listing-fight"):
            weight_class_el = fight.select_one(
                ".c-listing-fight__class--mobile .c-listing-fight__class-text"
            )
            fighter_red = _fighter_name(fight.select_one(".c-listing-fight__corner-name--red"))
            fighter_blue = _fighter_name(fight.select_one(".c-listing-fight__corner-name--blue"))
            if not fighter_red or not fighter_blue:
                continue
            fights.append(
                {
                    "fighter_red": fighter_red,
                    "fighter_blue": fighter_blue,
                    "weight_class": weight_class_el.get_text(strip=True) if weight_class_el else None,
                    "card_segment": segment_label,
                }
            )

    return {
        "event_name": event_name,
        "event_url": url,
        "date_timestamp": date_timestamp,
        "date_text": date_text,
        "venue": venue,
        "fights": fights,
    }


def slugify(url):
    # The url path segment (e.g. "ufc-330", "ufc-fight-night-august-22-2026") is
    # unique per event; the display name is not ("UFC Fight Night" repeats).
    return url.rstrip("/").rsplit("/", 1)[-1]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    event_urls = get_upcoming_event_urls()
    print(f"Found {len(event_urls)} upcoming events")

    for url in event_urls:
        event = scrape_event(url)
        slug = slugify(url)

        if not event["event_name"] or not event["fights"]:
            print(f"Skipping {url} — not yet published (no card data found)")
            time.sleep(1)
            continue

        out_path = OUTPUT_DIR / f"{slug}.json"
        out_path.write_text(json.dumps(event, indent=2))
        print(f"Saved {event['event_name']} ({len(event['fights'])} fights) -> {out_path}")
        time.sleep(1)  # be polite to ufc.com's servers


if __name__ == "__main__":
    main()
