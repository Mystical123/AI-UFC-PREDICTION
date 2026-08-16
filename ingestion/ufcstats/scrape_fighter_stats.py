"""Scrape structured fighter stats from UFCStats.com for every fighter that appears
in our already-scraped fight-card JSON files, saving one JSON file per fighter.

UFCStats.com sits behind a JS proof-of-work anti-bot challenge (an Anubis-style
check), so plain `requests` can't reach it -- the challenge never gets solved and
we just get the "Checking your browser..." page back. Playwright runs a real
(headless) browser that executes that JavaScript like a normal visitor would, so
by the time we read the page content we get the real, post-challenge HTML.
"""
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "http://ufcstats.com"
SEARCH_URL = f"{BASE_URL}/statistics/fighters/search"
FIGHT_CARDS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "fight_cards"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "ufcstats"

BIO_FIELDS = {
    "Height": "height",
    "Weight": "weight",
    "Reach": "reach",
    "STANCE": "stance",
    "DOB": "date_of_birth",
}
CAREER_STAT_FIELDS = {
    "SLpM": "sig_strikes_landed_per_min",
    "Str. Acc.": "sig_strike_accuracy",
    "SApM": "sig_strikes_absorbed_per_min",
    "Str. Def": "sig_strike_defense",
    "TD Avg.": "takedown_avg_per_15min",
    "TD Acc.": "takedown_accuracy",
    "TD Def.": "takedown_defense",
    "Sub. Avg.": "submission_avg_per_15min",
}


def collect_fighter_names():
    names = set()
    for path in FIGHT_CARDS_DIR.glob("*.json"):
        event = json.loads(path.read_text())
        for fight in event["fights"]:
            names.add(fight["fighter_red"])
            names.add(fight["fighter_blue"])
    return sorted(names)


def _box_list_fields(soup, wanted):
    """Pair each `<i class="...box-item-title...">Label:</i> value` list item with its label."""
    result = {}
    for li in soup.select(".b-list__box-list-item"):
        label_el = li.select_one(".b-list__box-item-title")
        if not label_el:
            continue
        label_text = label_el.get_text(strip=True)  # e.g. "Height:"
        label_key = label_text.rstrip(":")
        if label_key not in wanted:
            continue
        full_text = li.get_text(" ", strip=True)
        value = full_text[len(label_text):].strip()
        result[wanted[label_key]] = value or None
    return result


# A handful of Latin letters (Polish ł, Scandinavian ø, German ß, ...) aren't
# accent + base-letter combinations, so NFKD decomposition below can't strip
# them down to plain ASCII -- it just drops them, e.g. "Błachowicz" ->
# "Bachowicz" instead of "Blachowicz". Map the ones likely to show up in
# fighter names before falling back to NFKD for everything else.
_EXTRA_LETTER_MAP = str.maketrans(
    {"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O", "ß": "ss"}
)


def _normalize(s):
    # UFCStats stores names without diacritics ("Kaue", "Alvarez") while
    # UFC.com keeps them ("Kauê", "Álvarez") -- strip accents before comparing.
    s = s.translate(_EXTRA_LETTER_MAP)
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()


def find_fighter_url(page, name):
    # UFCStats' search only reliably matches a single token -- searching the full
    # "First Last" string returns zero results, so we search on the last name
    # and disambiguate among the (possibly many) results by full-name match.
    # It's also a substring match (e.g. "Van" matches "Ivan", "Evan", "Donovan"),
    # so a common last name can produce far more than one page of results --
    # page=all avoids silently missing a fighter who sorts onto page 2+.
    last_word = _normalize(name.split()[-1])
    page.goto(f"{SEARCH_URL}?query={quote(last_word)}&page=all", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=30000)
    soup = BeautifulSoup(page.content(), "html.parser")

    candidates = []
    for row in soup.select("tr.b-statistics__table-row"):
        links = row.select("a[href*='fighter-details']")
        if not links:
            continue
        first = links[0].get_text(strip=True)
        last = links[1].get_text(strip=True) if len(links) > 1 else ""
        candidates.append((f"{first} {last}".strip(), links[0]["href"]))

    target = _normalize(name)
    for candidate_name, href in candidates:
        if _normalize(candidate_name) == target:
            return href

    # UFC.com sometimes embeds a nickname in the display name that UFCStats
    # doesn't store (e.g. "Michael Venom Page" -> just "Michael Page") -- for a
    # 3+ word name, also try matching on first word + last word only.
    words = name.split()
    if len(words) > 2:
        trimmed_target = _normalize(f"{words[0]} {words[-1]}")
        for candidate_name, href in candidates:
            if _normalize(candidate_name) == trimmed_target:
                return href

    # Fall back to a single unambiguous result.
    if len(candidates) == 1:
        return candidates[0][1]

    return None


def scrape_fighter(page, url):
    page.goto(url, timeout=30000)
    page.wait_for_load_state("networkidle", timeout=30000)
    soup = BeautifulSoup(page.content(), "html.parser")

    name_el = soup.select_one(".b-content__title-highlight")
    record_el = soup.select_one(".b-content__title-record")

    fighter = {
        "name": name_el.get_text(strip=True) if name_el else None,
        "record": record_el.get_text(strip=True).replace("Record:", "").strip()
        if record_el
        else None,
        "profile_url": url,
    }
    fighter.update(_box_list_fields(soup, BIO_FIELDS))
    fighter.update(_box_list_fields(soup, CAREER_STAT_FIELDS))
    return fighter


def slugify(name):
    # Normalize accented letters to their closest ASCII form first (e.g. "Uroš
    # Medić" -> "uros medic") so they end up in the filename instead of being
    # silently deleted by the regex below.
    return re.sub(r"[^a-z0-9]+", "-", _normalize(name)).strip("-")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    names = collect_fighter_names()
    print(f"Looking up {len(names)} fighters from scraped fight cards")

    unmatched = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for name in names:
            out_path = OUTPUT_DIR / f"{slugify(name)}.json"
            if out_path.exists():
                continue  # already scraped in a previous run

            url = find_fighter_url(page, name)
            if not url:
                print(f"No unambiguous UFCStats match for '{name}' -- skipping")
                unmatched.append(name)
                time.sleep(1)
                continue

            fighter = scrape_fighter(page, url)
            out_path.write_text(json.dumps(fighter, indent=2))
            print(f"Saved {fighter['name']} ({fighter['record']}) -> {out_path}")
            time.sleep(1)

        browser.close()

    if unmatched:
        print(f"\n{len(unmatched)} fighters need manual lookup: {unmatched}")


if __name__ == "__main__":
    main()
