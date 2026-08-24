-- Structured data (events, fighters, fights) is plain SQL, queried directly.
-- RAG content (rag_chunks) is the only embedded/vector-searched table.
-- See CLAUDE.md's "Key principle" -- don't blur this line.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS events (
    event_slug TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    date_timestamp BIGINT,
    date_text TEXT,
    venue TEXT,
    event_url TEXT
);

CREATE TABLE IF NOT EXISTS fighters (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    record TEXT,
    height_inches REAL,
    weight_lbs REAL,
    reach_inches REAL,
    stance TEXT,
    date_of_birth DATE,
    sig_strikes_landed_per_min REAL,
    sig_strike_accuracy_pct REAL,
    sig_strikes_absorbed_per_min REAL,
    sig_strike_defense_pct REAL,
    takedown_avg_per_15min REAL,
    takedown_accuracy_pct REAL,
    takedown_defense_pct REAL,
    submission_avg_per_15min REAL,
    profile_url TEXT,
    -- Derived features (computed, not scraped -- see db/derive_features.py):
    style TEXT,          -- wrestler / grappler / striker / balanced
    age INTEGER,
    win_streak INTEGER,
    -- Sourced from UFC.com's own fight-card corner images (data/raw/fight_cards),
    -- not scraped separately -- see db/load_data.py.
    image_url TEXT
);

-- ADD COLUMN IF NOT EXISTS so re-running this file against an already-created
-- table (from before these columns existed) is still idempotent.
ALTER TABLE fighters ADD COLUMN IF NOT EXISTS style TEXT;
ALTER TABLE fighters ADD COLUMN IF NOT EXISTS age INTEGER;
ALTER TABLE fighters ADD COLUMN IF NOT EXISTS win_streak INTEGER;
ALTER TABLE fighters ADD COLUMN IF NOT EXISTS image_url TEXT;

CREATE TABLE IF NOT EXISTS fights (
    id SERIAL PRIMARY KEY,
    event_slug TEXT REFERENCES events(event_slug),
    fighter_red_slug TEXT REFERENCES fighters(slug),
    fighter_blue_slug TEXT REFERENCES fighters(slug),
    fighter_red_name TEXT NOT NULL,
    fighter_blue_name TEXT NOT NULL,
    weight_class TEXT,
    card_segment TEXT,
    UNIQUE (event_slug, fighter_red_name, fighter_blue_name)
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    event_slug TEXT,
    fighter_red TEXT,
    fighter_blue TEXT,
    title TEXT,
    author TEXT,
    url TEXT,
    text TEXT NOT NULL,
    embedding VECTOR(384)
);

-- HNSW: approximate nearest-neighbor index, so cosine-similarity search over
-- rag_chunks stays fast as the table grows past what a full scan could do
-- quickly. cosine ops since sentence-transformers embeddings are meant to be
-- compared by cosine similarity, not raw distance.
CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
    ON rag_chunks USING hnsw (embedding vector_cosine_ops);

-- Predictions are generated once per fight and cached here, not regenerated
-- on every page view -- an LLM call is nondeterministic (temperature > 0),
-- so re-generating on every request made the displayed pick/confidence
-- change from one visit to the next, which reads as broken/untrustworthy
-- for a "prediction" feature. One fight -> one stored prediction.
CREATE TABLE IF NOT EXISTS predictions (
    fight_id INTEGER PRIMARY KEY REFERENCES fights(id),
    prediction_text TEXT NOT NULL,
    citations JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
