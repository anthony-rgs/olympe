"""
Usage:
  docker compose exec owl python -m app.cli tracks
  docker compose exec owl python -m app.cli artists
  docker compose exec owl python -m app.cli all
"""

import sys
from .ingest_tracks import ingest_tracks
from .ingest_artists import ingest_artists

# Main function that manages the launch of all scripts
def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    cmd = (argv[0] if argv else "all").lower()
    if cmd not in {"tracks", "artists", "all"}:
        print("Usage: python -m app.cli [tracks|artists|all]")
        return 2
    if cmd in {"tracks", "all"}:
        res = ingest_tracks()
        print("[OWL] tracks →", res)
    if cmd in {"artists", "all"}:
        res = ingest_artists()
        print("[OWL] artists →", res)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
