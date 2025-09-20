from typing import Optional

# Upsert an album by case-insensitive title: insert if new, otherwise update nullable fields; returns the album ID.
def upsert_album(conn, *, title: str,
  cover_url: Optional[str],
  release_year: Optional[int]) -> int:
    """
    Source: tracks.json — uniqueness by title (CITEXT).
    """

    sql = """
    INSERT INTO albums(title, cover_url, release_year)
    VALUES (%s, %s, %s)
    ON CONFLICT (title) DO UPDATE SET
      cover_url    = COALESCE(EXCLUDED.cover_url, albums.cover_url),
      release_year = COALESCE(EXCLUDED.release_year, albums.release_year)
    RETURNING id;
    """
    with conn.cursor() as cur:
      cur.execute(sql, (title, cover_url, release_year))
      return cur.fetchone()[0]