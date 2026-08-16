"""Scrape Reddit discussion (r/mma + r/ufc) for every fight in our scraped fight
cards, saving one JSON file per fight to data/raw/reddit/<event_slug>/.

Uses PRAW (the official Reddit API wrapper) rather than scraping reddit.com's
HTML -- Reddit has a real, free API for this, so there's no need to fight an
anti-bot system the way we did for UFCStats.
"""
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import praw
from dotenv import load_dotenv

FIGHT_CARDS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "fight_cards"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "reddit"

SUBMISSIONS_PER_FIGHT = 5
MAX_COMMENTS_PER_SUBMISSION = 20
IGNORED_COMMENT_AUTHORS = {"AutoModerator"}
IGNORED_COMMENT_BODIES = {"[deleted]", "[removed]"}


def _normalize(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", _normalize(name)).strip("-")


def get_reddit_client():
    load_dotenv()
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    user_agent = os.getenv("REDDIT_USER_AGENT", "").strip()

    missing = [
        name
        for name, val in [
            ("REDDIT_CLIENT_ID", client_id),
            ("REDDIT_CLIENT_SECRET", client_secret),
            ("REDDIT_USER_AGENT", user_agent),
        ]
        if not val
    ]
    if missing:
        sys.exit(
            "Missing Reddit credentials in .env: "
            + ", ".join(missing)
            + ". Create a 'script' app at https://www.reddit.com/prefs/apps and fill in .env."
        )

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


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


def _last_name(full_name):
    return full_name.split()[-1]


def search_fight(reddit, fighter_red, fighter_blue):
    query = f"{_last_name(fighter_red)} {_last_name(fighter_blue)}"
    subreddit = reddit.subreddit("mma+ufc")

    red_key = _normalize(_last_name(fighter_red))
    blue_key = _normalize(_last_name(fighter_blue))

    submissions = []
    for submission in subreddit.search(query, sort="relevance", time_filter="all", limit=SUBMISSIONS_PER_FIGHT):
        title_norm = _normalize(submission.title)
        # Post-filter: keep only threads that actually name both fighters --
        # Reddit's search is fuzzy/relevance-ranked, not an exact match.
        if red_key not in title_norm or blue_key not in title_norm:
            continue

        submission.comment_sort = "top"
        submission.comments.replace_more(limit=0)

        comments = []
        for comment in submission.comments:
            if len(comments) >= MAX_COMMENTS_PER_SUBMISSION:
                break
            author = str(comment.author) if comment.author else None
            if author in IGNORED_COMMENT_AUTHORS:
                continue
            if comment.body in IGNORED_COMMENT_BODIES:
                continue
            comments.append(
                {
                    "author": author,
                    "body": comment.body,
                    "score": comment.score,
                    "created_utc": comment.created_utc,
                }
            )

        submissions.append(
            {
                "title": submission.title,
                "selftext": submission.selftext,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "subreddit": submission.subreddit.display_name,
                "permalink": f"https://reddit.com{submission.permalink}",
                "created_utc": submission.created_utc,
                "comments": comments,
            }
        )

    return submissions


def main():
    reddit = get_reddit_client()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fights = collect_fights()
    print(f"Searching Reddit for {len(fights)} fights")

    for fight in fights:
        event_dir = OUTPUT_DIR / fight["event_slug"]
        event_dir.mkdir(exist_ok=True)
        out_path = event_dir / f"{slugify(fight['fighter_red'])}-vs-{slugify(fight['fighter_blue'])}.json"
        if out_path.exists():
            continue

        submissions = search_fight(reddit, fight["fighter_red"], fight["fighter_blue"])
        result = {**fight, "submissions": submissions}
        out_path.write_text(json.dumps(result, indent=2))
        print(
            f"Saved {fight['fighter_red']} vs {fight['fighter_blue']} "
            f"({len(submissions)} threads) -> {out_path}"
        )
        time.sleep(1)


if __name__ == "__main__":
    main()
