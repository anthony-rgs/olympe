# Upsert the singleton tracks_meta row (id=1): insert if missing, otherwise update link/cover fields
def upsert_tracks_meta(conn, *, link: str | None, cover_img: str | None, cover_artist: str | None) -> None:
  with conn.cursor() as cur:
    cur.execute("""
      INSERT INTO tracks_meta(id, link, cover_img, cover_artist)
      VALUES (1, %s, %s, %s)
      ON CONFLICT (id) DO UPDATE SET
        link = EXCLUDED.link,
        cover_img = EXCLUDED.cover_img,
        cover_artist = EXCLUDED.cover_artist
    """, (link, cover_img, cover_artist))
