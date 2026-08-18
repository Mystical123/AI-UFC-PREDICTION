"""Chunk RAG-source text (Sherdog/MMA Junkie/ESPN articles, Reddit posts/comments)
into sentence-grouped windows and embed each chunk locally with sentence-transformers.

This is step 2 of the build order: chunking + embeddings only, saved to a single
local JSONL file. Loading these into a pgvector table is step 3, a separate task.
"""
import json
import re
from pathlib import Path

from sentence_transformers import SentenceTransformer

DATA_RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "chunks.jsonl"
MODEL_NAME = "all-MiniLM-L6-v2"

# ~150 words is comfortably under all-MiniLM-L6-v2's 256-token limit even with
# a title prefixed on for context. OVERLAP_SENTENCES repeats the last sentence
# of a chunk as the first sentence of the next, so a fact split across a chunk
# boundary isn't orphaned in only one of the two chunks.
TARGET_WORDS = 150
OVERLAP_SENTENCES = 1

# Naive but effective: split after sentence-ending punctuation followed by
# whitespace and a capital letter or opening quote. Won't be perfect on every
# abbreviation, but chunking only needs reasonable boundaries, not perfect ones.
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"“])')


def split_sentences(text):
    text = (text or "").strip()
    if not text:
        return []
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]


def group_into_chunks(sentences):
    if not sentences:
        return []
    chunks = []
    current = []
    current_words = 0

    for i, sentence in enumerate(sentences):
        current.append(sentence)
        current_words += len(sentence.split())
        is_last = i == len(sentences) - 1
        if current_words >= TARGET_WORDS and not is_last:
            chunks.append(" ".join(current))
            current = current[-OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else []
            current_words = sum(len(s.split()) for s in current)

    if current:
        chunks.append(" ".join(current))
    return chunks


def collect_article_chunks():
    """Sherdog/MMA Junkie/ESPN: chunk each article's body_text."""
    records = []
    for source_dir in ("sherdog", "mmajunkie", "espn"):
        source_path = DATA_RAW / source_dir
        if not source_path.exists():
            continue
        for path in sorted(source_path.glob("**/*.json")):
            fight = json.loads(path.read_text())
            for i, article in enumerate(fight.get("articles", [])):
                title = article.get("title") or ""
                chunk_texts = group_into_chunks(split_sentences(article.get("body_text")))
                for j, chunk_text in enumerate(chunk_texts):
                    records.append(
                        {
                            "chunk_id": f"{source_dir}:{path.stem}:{i}:{j}",
                            "source": source_dir,
                            "event_slug": fight["event_slug"],
                            "fighter_red": fight["fighter_red"],
                            "fighter_blue": fight["fighter_blue"],
                            "title": article.get("title"),
                            "author": article.get("author"),
                            "url": article.get("url"),
                            "text": chunk_text,
                            "embedding_input": f"{title}. {chunk_text}".strip(". "),
                        }
                    )
    return records


def collect_reddit_chunks():
    """Reddit: each submission (title+selftext, chunked) and each top-level
    comment (usually short enough to stand as a single chunk on its own)."""
    records = []
    source_path = DATA_RAW / "reddit"
    if not source_path.exists():
        return records

    for path in sorted(source_path.glob("**/*.json")):
        fight = json.loads(path.read_text())
        for i, submission in enumerate(fight.get("submissions", [])):
            title = submission["title"]
            body = (submission.get("selftext") or "").strip()
            full_text = f"{title}. {body}".strip(". ") if body else title
            chunk_texts = group_into_chunks(split_sentences(full_text)) or [full_text]
            for j, chunk_text in enumerate(chunk_texts):
                records.append(
                    {
                        "chunk_id": f"reddit:{path.stem}:submission:{i}:{j}",
                        "source": "reddit",
                        "event_slug": fight["event_slug"],
                        "fighter_red": fight["fighter_red"],
                        "fighter_blue": fight["fighter_blue"],
                        "title": title,
                        "author": None,
                        "url": submission.get("permalink"),
                        "text": chunk_text,
                        "embedding_input": chunk_text,
                    }
                )
            for k, comment in enumerate(submission.get("comments", [])):
                body = (comment.get("body") or "").strip()
                if not body:
                    continue
                records.append(
                    {
                        "chunk_id": f"reddit:{path.stem}:comment:{i}:{k}",
                        "source": "reddit",
                        "event_slug": fight["event_slug"],
                        "fighter_red": fight["fighter_red"],
                        "fighter_blue": fight["fighter_blue"],
                        "title": title,
                        "author": comment.get("author"),
                        "url": submission.get("permalink"),
                        "text": body,
                        "embedding_input": body,
                    }
                )
    return records


def main():
    records = collect_article_chunks() + collect_reddit_chunks()
    print(f"Built {len(records)} chunks from raw data")

    print(f"Loading embedding model ({MODEL_NAME})...")
    model = SentenceTransformer(MODEL_NAME)

    print("Embedding chunks...")
    texts = [r["embedding_input"] for r in records]
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        for record, embedding in zip(records, embeddings):
            record = {k: v for k, v in record.items() if k != "embedding_input"}
            record["embedding"] = embedding.tolist()
            f.write(json.dumps(record) + "\n")

    print(f"Saved {len(records)} chunks with embeddings -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
