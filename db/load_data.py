"""Apply the schema and load our scraped/processed data into local Postgres:
events + fights (from fight_cards), fighters (from ufcstats, with proper type
parsing), and rag_chunks (from the embedded chunks.jsonl).

Structured tables (events, fighters, fights) hold exact data, queried
directly. rag_chunks is the only embedded/vector-searched table -- see
CLAUDE.md's "Key principle" on not blurring that line.
"""
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATA_RAW = ROOT / "data" / "raw"
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection():
    conn = psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    register_vector(conn)
    return conn


def slugify(name):
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def parse_height(value):
    if not value:
        return None
    m = re.match(r"(\d+)'\s*(\d+)\"", value)
    return float(int(m.group(1)) * 12 + int(m.group(2))) if m else None


def parse_leading_number(value):
    if not value:
        return None
    m = re.match(r"([\d.]+)", value)
    return float(m.group(1)) if m else None


def parse_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%b %d, %Y").date()
    except ValueError:
        return None


def apply_schema(conn):
    conn.execute(SCHEMA_PATH.read_text())
    conn.commit()
    print("Schema applied.")


def load_fighters(conn):
    count = 0
    valid_slugs = set()
    with conn.cursor() as cur:
        for path in sorted((DATA_RAW / "ufcstats").glob("*.json")):
            fighter = json.loads(path.read_text())
            slug = path.stem
            cur.execute(
                """
                INSERT INTO fighters (
                    slug, name, record, height_inches, weight_lbs, reach_inches, stance,
                    date_of_birth, sig_strikes_landed_per_min, sig_strike_accuracy_pct,
                    sig_strikes_absorbed_per_min, sig_strike_defense_pct,
                    takedown_avg_per_15min, takedown_accuracy_pct, takedown_defense_pct,
                    submission_avg_per_15min, profile_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name, record = EXCLUDED.record,
                    height_inches = EXCLUDED.height_inches, weight_lbs = EXCLUDED.weight_lbs,
                    reach_inches = EXCLUDED.reach_inches, stance = EXCLUDED.stance,
                    date_of_birth = EXCLUDED.date_of_birth,
                    sig_strikes_landed_per_min = EXCLUDED.sig_strikes_landed_per_min,
                    sig_strike_accuracy_pct = EXCLUDED.sig_strike_accuracy_pct,
                    sig_strikes_absorbed_per_min = EXCLUDED.sig_strikes_absorbed_per_min,
                    sig_strike_defense_pct = EXCLUDED.sig_strike_defense_pct,
                    takedown_avg_per_15min = EXCLUDED.takedown_avg_per_15min,
                    takedown_accuracy_pct = EXCLUDED.takedown_accuracy_pct,
                    takedown_defense_pct = EXCLUDED.takedown_defense_pct,
                    submission_avg_per_15min = EXCLUDED.submission_avg_per_15min,
                    profile_url = EXCLUDED.profile_url
                """,
                (
                    slug,
                    fighter["name"],
                    fighter.get("record"),
                    parse_height(fighter.get("height")),
                    parse_leading_number(fighter.get("weight")),
                    parse_leading_number(fighter.get("reach")),
                    fighter.get("stance"),
                    parse_date(fighter.get("date_of_birth")),
                    parse_float(fighter.get("sig_strikes_landed_per_min")),
                    parse_leading_number(fighter.get("sig_strike_accuracy")),
                    parse_float(fighter.get("sig_strikes_absorbed_per_min")),
                    parse_leading_number(fighter.get("sig_strike_defense")),
                    parse_float(fighter.get("takedown_avg_per_15min")),
                    parse_leading_number(fighter.get("takedown_accuracy")),
                    parse_leading_number(fighter.get("takedown_defense")),
                    parse_float(fighter.get("submission_avg_per_15min")),
                    fighter.get("profile_url"),
                ),
            )
            valid_slugs.add(slug)
            count += 1
    conn.commit()
    print(f"Loaded {count} fighters.")
    return valid_slugs


def load_events_and_fights(conn, valid_fighter_slugs):
    events, fights = 0, 0
    with conn.cursor() as cur:
        for path in sorted((DATA_RAW / "fight_cards").glob("*.json")):
            event = json.loads(path.read_text())
            event_slug = path.stem
            cur.execute(
                """
                INSERT INTO events (event_slug, event_name, date_timestamp, date_text, venue, event_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_slug) DO UPDATE SET
                    event_name = EXCLUDED.event_name, date_timestamp = EXCLUDED.date_timestamp,
                    date_text = EXCLUDED.date_text, venue = EXCLUDED.venue, event_url = EXCLUDED.event_url
                """,
                (
                    event_slug,
                    event["event_name"],
                    event.get("date_timestamp"),
                    event.get("date_text"),
                    event.get("venue"),
                    event.get("event_url"),
                ),
            )
            events += 1

            for fight in event["fights"]:
                red_slug = slugify(fight["fighter_red"])
                blue_slug = slugify(fight["fighter_blue"])
                red_slug = red_slug if red_slug in valid_fighter_slugs else None
                blue_slug = blue_slug if blue_slug in valid_fighter_slugs else None

                cur.execute(
                    """
                    INSERT INTO fights (
                        event_slug, fighter_red_slug, fighter_blue_slug,
                        fighter_red_name, fighter_blue_name, weight_class, card_segment
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_slug, fighter_red_name, fighter_blue_name) DO NOTHING
                    """,
                    (
                        event_slug,
                        red_slug,
                        blue_slug,
                        fight["fighter_red"],
                        fight["fighter_blue"],
                        fight.get("weight_class"),
                        fight.get("card_segment"),
                    ),
                )
                fights += 1

                # Fighter photos come from UFC.com's own fight-card corner
                # images (this file), not a separate scrape -- propagate onto
                # the fighters row here rather than adding a new ingestion step.
                for slug, image_url in (
                    (red_slug, fight.get("fighter_red_image_url")),
                    (blue_slug, fight.get("fighter_blue_image_url")),
                ):
                    if slug and image_url:
                        cur.execute("UPDATE fighters SET image_url = %s WHERE slug = %s", (image_url, slug))
    conn.commit()
    print(f"Loaded {events} events, {fights} fights.")


def load_rag_chunks(conn):
    if not CHUNKS_PATH.exists():
        print("No chunks.jsonl found -- run processing/chunk_and_embed.py first. Skipping.")
        return
    count = 0
    with conn.cursor() as cur, CHUNKS_PATH.open() as f:
        for line in f:
            chunk = json.loads(line)
            cur.execute(
                """
                INSERT INTO rag_chunks (
                    chunk_id, source, event_slug, fighter_red, fighter_blue,
                    title, author, url, text, embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET text = EXCLUDED.text, embedding = EXCLUDED.embedding
                """,
                (
                    chunk["chunk_id"],
                    chunk["source"],
                    chunk.get("event_slug"),
                    chunk.get("fighter_red"),
                    chunk.get("fighter_blue"),
                    chunk.get("title"),
                    chunk.get("author"),
                    chunk.get("url"),
                    chunk["text"],
                    chunk["embedding"],
                ),
            )
            count += 1
    conn.commit()
    print(f"Loaded {count} RAG chunks.")


def main():
    conn = get_connection()
    apply_schema(conn)
    valid_fighter_slugs = load_fighters(conn)
    load_events_and_fights(conn, valid_fighter_slugs)
    load_rag_chunks(conn)
    conn.close()


if __name__ == "__main__":
    main()
