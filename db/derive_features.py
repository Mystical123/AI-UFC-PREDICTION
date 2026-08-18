"""Compute derived features on top of the fighters table: style classification
(rule-based from UFCStats numbers), age, and win streak (from fight history).

Per CLAUDE.md, rule-based style classification from UFCStats numbers is the
*primary* method -- always available since every fighter has these numbers,
unlike bio-text scraping (secondary method, not implemented -- see CLAUDE.md's
"Confirmed 2026-08-15" note on why).
"""
import json
import os
import statistics
from datetime import date
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
UFCSTATS_DIR = ROOT / "data" / "raw" / "ufcstats"


def get_connection():
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def compute_win_streak(fight_history):
    """Count consecutive wins from the most recent fight backward. Stops at
    the first non-win (loss/draw/NC) or the end of the fighter's history."""
    streak = 0
    for fight in fight_history:
        if fight.get("result") == "win":
            streak += 1
        else:
            break
    return streak


def zscore(value, mean, stdev):
    if value is None or stdev == 0:
        return 0.0
    return (value - mean) / stdev


def classify_style(td_z, sub_z, slpm_z):
    """Whichever signal is most standard deviations above the fighter
    population's mean wins, as long as it clears a minimum bar -- otherwise
    no single dimension is obviously dominant, so 'balanced' is the honest
    label rather than forcing a guess."""
    scores = {"wrestler": td_z, "grappler": sub_z, "striker": slpm_z}
    best_style, best_z = max(scores.items(), key=lambda kv: kv[1])
    return best_style if best_z >= 0.5 else "balanced"


def compute_age(dob):
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def main():
    conn = get_connection()

    rows = conn.execute(
        "SELECT slug, takedown_avg_per_15min, submission_avg_per_15min, "
        "sig_strikes_landed_per_min, date_of_birth FROM fighters"
    ).fetchall()

    td_avgs = [r[1] for r in rows if r[1] is not None]
    sub_avgs = [r[2] for r in rows if r[2] is not None]
    slpms = [r[3] for r in rows if r[3] is not None]
    td_mean, td_std = statistics.mean(td_avgs), statistics.pstdev(td_avgs)
    sub_mean, sub_std = statistics.mean(sub_avgs), statistics.pstdev(sub_avgs)
    slpm_mean, slpm_std = statistics.mean(slpms), statistics.pstdev(slpms)

    updated = 0
    with conn.cursor() as cur:
        for slug, td_avg, sub_avg, slpm, dob in rows:
            style = classify_style(
                zscore(td_avg, td_mean, td_std),
                zscore(sub_avg, sub_mean, sub_std),
                zscore(slpm, slpm_mean, slpm_std),
            )
            age = compute_age(dob)

            history_path = UFCSTATS_DIR / f"{slug}.json"
            win_streak = None
            if history_path.exists():
                fighter_json = json.loads(history_path.read_text())
                if "fight_history" in fighter_json:
                    win_streak = compute_win_streak(fighter_json["fight_history"])

            cur.execute(
                "UPDATE fighters SET style = %s, age = %s, win_streak = %s WHERE slug = %s",
                (style, age, win_streak, slug),
            )
            updated += 1
    conn.commit()
    conn.close()
    print(f"Updated derived features for {updated} fighters.")


if __name__ == "__main__":
    main()
