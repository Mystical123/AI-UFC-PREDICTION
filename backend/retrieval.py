"""Semantic retrieval over rag_chunks for the chatbot.

Unlike the prediction endpoint's exact metadata filter (we already know which
chunks are about a given fight, since they were scraped specifically for it),
the chatbot handles open-ended user questions -- we don't know in advance
which chunks are relevant, so this needs real vector similarity search.
"""
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"  # must match processing/chunk_and_embed.py -- a
# different model produces vectors in a different space, not comparable to
# what's already stored in rag_chunks.embedding

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def search_chunks(cur, query, k=5, event_slug=None, fighter=None):
    query_vec = get_model().encode(query)

    sql = (
        "SELECT source, title, author, url, text, "
        "embedding <=> %s AS distance FROM rag_chunks"
    )
    params = [query_vec]
    filters = []
    if event_slug:
        filters.append("event_slug = %s")
        params.append(event_slug)
    if fighter:
        filters.append("(fighter_red = %s OR fighter_blue = %s)")
        params.extend([fighter, fighter])
    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY distance LIMIT %s"
    params.append(k)

    cur.execute(sql, params)
    return cur.fetchall()
