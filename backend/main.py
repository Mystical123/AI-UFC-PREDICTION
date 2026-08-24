"""FastAPI backend: fight cards, fighter/fight detail, predictions, and chat.

Structured endpoints (events, fighters, fights) query Postgres directly.
Predictions combine stats/derived features with RAG commentary (exact
metadata filter) fed to Groq. The chatbot uses real pgvector similarity
search instead, since a user's question is open-ended.
"""
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.db import get_connection
from backend.llm import generate_chat_response, generate_prediction
from backend.retrieval import search_chunks
from backend.schemas import (
    ChatRequest,
    ChatResponse,
    EventDetail,
    EventSummary,
    FightDetail,
    FightSummary,
    FighterDetail,
    PredictionResponse,
)

app = FastAPI(title="AI UFC Prediction API")

# The Vite dev server proxies /api -> here, so the browser never actually
# makes a cross-origin request in local dev -- this matters once the
# frontend is deployed somewhere that calls the API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FIGHTER_COLUMNS = """
    slug, name, record, height_inches, weight_lbs, reach_inches, stance,
    date_of_birth, sig_strikes_landed_per_min, sig_strike_accuracy_pct,
    sig_strikes_absorbed_per_min, sig_strike_defense_pct,
    takedown_avg_per_15min, takedown_accuracy_pct, takedown_defense_pct,
    submission_avg_per_15min, profile_url, style, age, win_streak, image_url
"""


@app.get("/events", response_model=list[EventSummary])
def list_events(conn: Connection = Depends(get_connection)):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT event_slug, event_name, date_timestamp, date_text, venue "
            "FROM events ORDER BY date_timestamp ASC NULLS LAST"
        )
        return cur.fetchall()


@app.get("/events/{event_slug}", response_model=EventDetail)
def get_event(event_slug: str, conn: Connection = Depends(get_connection)):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT event_slug, event_name, date_timestamp, date_text, venue "
            "FROM events WHERE event_slug = %s",
            (event_slug,),
        )
        event = cur.fetchone()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        cur.execute(
            """
            SELECT f.id, f.event_slug, f.fighter_red_name, f.fighter_blue_name,
                   f.weight_class, f.card_segment,
                   fr.image_url AS fighter_red_image_url, fb.image_url AS fighter_blue_image_url
            FROM fights f
            LEFT JOIN fighters fr ON f.fighter_red_slug = fr.slug
            LEFT JOIN fighters fb ON f.fighter_blue_slug = fb.slug
            WHERE f.event_slug = %s ORDER BY f.id
            """,
            (event_slug,),
        )
        event["fights"] = cur.fetchall()
        return event


@app.get("/fighters/{slug}", response_model=FighterDetail)
def get_fighter(slug: str, conn: Connection = Depends(get_connection)):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {FIGHTER_COLUMNS} FROM fighters WHERE slug = %s", (slug,))
        fighter = cur.fetchone()
        if not fighter:
            raise HTTPException(status_code=404, detail="Fighter not found")
        return fighter


def _fetch_fight_detail(cur, fight_id):
    """Shared by /fights/{id} and /fights/{id}/prediction. Keeps the raw
    fighter_{red,blue}_name fields (not part of the FightDetail response
    model, so FastAPI/Pydantic silently drops them from that endpoint's
    output) since rag_chunks is keyed on those exact display-name strings,
    not on the fighters table's slug -- and a fight's fighter can be None
    (2 of 306 fighters have no UFCStats match) while the name is still needed."""
    cur.execute(
        """
        SELECT f.id, f.weight_class, f.card_segment,
               f.fighter_red_slug, f.fighter_blue_slug,
               f.fighter_red_name, f.fighter_blue_name,
               e.event_slug, e.event_name, e.date_timestamp, e.date_text, e.venue
        FROM fights f
        JOIN events e ON f.event_slug = e.event_slug
        WHERE f.id = %s
        """,
        (fight_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    def fetch_fighter(slug):
        if not slug:
            return None
        cur.execute(f"SELECT {FIGHTER_COLUMNS} FROM fighters WHERE slug = %s", (slug,))
        return cur.fetchone()

    return {
        "id": row["id"],
        "weight_class": row["weight_class"],
        "card_segment": row["card_segment"],
        "event": {
            "event_slug": row["event_slug"],
            "event_name": row["event_name"],
            "date_timestamp": row["date_timestamp"],
            "date_text": row["date_text"],
            "venue": row["venue"],
        },
        "fighter_red": fetch_fighter(row["fighter_red_slug"]),
        "fighter_blue": fetch_fighter(row["fighter_blue_slug"]),
        "fighter_red_name": row["fighter_red_name"],
        "fighter_blue_name": row["fighter_blue_name"],
    }


@app.get("/fights/{fight_id}", response_model=FightDetail)
def get_fight(fight_id: int, conn: Connection = Depends(get_connection)):
    with conn.cursor(row_factory=dict_row) as cur:
        fight = _fetch_fight_detail(cur, fight_id)
        if not fight:
            raise HTTPException(status_code=404, detail="Fight not found")
        return fight


@app.get("/fights/{fight_id}/prediction", response_model=PredictionResponse)
def get_prediction(fight_id: int, conn: Connection = Depends(get_connection)):
    with conn.cursor(row_factory=dict_row) as cur:
        # Predictions are generated once per fight and cached -- an LLM call
        # is nondeterministic, so regenerating on every request made the
        # displayed pick/confidence change between visits. See db/schema.sql.
        cur.execute(
            "SELECT prediction_text, citations FROM predictions WHERE fight_id = %s",
            (fight_id,),
        )
        cached = cur.fetchone()
        if cached:
            return {"fight_id": fight_id, "prediction": cached["prediction_text"], "citations": cached["citations"]}

        fight = _fetch_fight_detail(cur, fight_id)
        if not fight:
            raise HTTPException(status_code=404, detail="Fight not found")

        cur.execute(
            """
            SELECT source, title, author, url, text FROM rag_chunks
            WHERE event_slug = %s AND fighter_red = %s AND fighter_blue = %s
            LIMIT 20
            """,
            (fight["event"]["event_slug"], fight["fighter_red_name"], fight["fighter_blue_name"]),
        )
        chunks = cur.fetchall()

        prediction_text = generate_prediction(fight, chunks)

        cur.execute(
            """
            INSERT INTO predictions (fight_id, prediction_text, citations)
            VALUES (%s, %s, %s)
            ON CONFLICT (fight_id) DO UPDATE SET
                prediction_text = EXCLUDED.prediction_text, citations = EXCLUDED.citations, created_at = now()
            """,
            (fight_id, prediction_text, Jsonb(chunks)),
        )
    conn.commit()

    return {
        "fight_id": fight_id,
        "prediction": prediction_text,
        "citations": chunks,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, conn: Connection = Depends(get_connection)):
    with conn.cursor(row_factory=dict_row) as cur:
        chunks = search_chunks(
            cur, request.message, k=5, event_slug=request.event_slug, fighter=request.fighter
        )
    response_text = generate_chat_response(request.message, chunks)
    return {"response": response_text, "citations": chunks}
