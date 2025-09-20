import os
from typing import Final

# URL Postgres (ex: postgresql://user:pass@host:5432/db)
DATABASE_URL: Final[str] = os.getenv("DATABASE_URL")

# JSON sources
TRACKS_PATH:  Final[str] = os.getenv("TRACKS_PATH",  "/data/collections/billion-club/tracks")
ARTISTS_PATH: Final[str] = os.getenv("ARTISTS_PATH", "/data/collections/billion-club/artists")
