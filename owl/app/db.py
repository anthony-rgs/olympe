import psycopg
from contextlib import contextmanager
from .config import DATABASE_URL

@contextmanager
def get_conn():
    # psycopg v3 auto-commit on context exit (if no exception)
    with psycopg.connect(DATABASE_URL) as conn:
        yield conn
