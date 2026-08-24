"""Shared Postgres connection pool for the API.

A pool (vs. opening a new connection per request) matters once there's more
than one request in flight -- opening a fresh TCP + auth handshake to Postgres
on every request is real, avoidable latency. The pool keeps a handful of
connections open and hands them out as requests come in.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_CONNINFO = (
    f"host={os.environ['POSTGRES_HOST']} port={os.environ['POSTGRES_PORT']} "
    f"dbname={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']} "
    f"password={os.environ['POSTGRES_PASSWORD']}"
)

pool = ConnectionPool(_CONNINFO, min_size=1, max_size=5, configure=register_vector, open=True)


def get_connection():
    """FastAPI dependency: yields a pooled connection, returns it when the request ends."""
    with pool.connection() as conn:
        yield conn
