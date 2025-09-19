CREATE TABLE IF NOT EXISTS artists (
  id                 BIGSERIAL PRIMARY KEY,
  artist_name        CITEXT NOT NULL,
  artist_img         TEXT,
  monthly_listeners  BIGINT,
  visit_count        INTEGER NOT NULL DEFAULT 0,
  created_at         TIMESTAMPTZ DEFAULT now(),
  updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS albums (
  id            BIGSERIAL PRIMARY KEY,
  title         CITEXT NOT NULL,
  cover_url     TEXT,
  release_year  INTEGER,
  visit_count   INTEGER NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS titles (
  id             BIGSERIAL PRIMARY KEY,
  name           CITEXT NOT NULL,
  streams_count  BIGINT,
  played_count   INTEGER NOT NULL DEFAULT 0,
  track_time     TEXT,
  cover_url      TEXT,
  iframe         TEXT,
  album_id       BIGINT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_titles_album_id ON titles(album_id);

CREATE TABLE IF NOT EXISTS album_artists (
  album_id   BIGINT NOT NULL REFERENCES albums(id)  ON DELETE CASCADE,
  artist_id  BIGINT NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
  role       TEXT,
  PRIMARY KEY (album_id, artist_id)
);

CREATE TABLE IF NOT EXISTS title_artists (
  title_id   BIGINT NOT NULL REFERENCES titles(id)  ON DELETE CASCADE,
  artist_id  BIGINT NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
  role       TEXT,
  PRIMARY KEY (title_id, artist_id)
);

CREATE TABLE IF NOT EXISTS tracks_meta (
  id           INTEGER PRIMARY KEY CHECK (id = 1),
  link         TEXT,
  cover_img    TEXT,
  cover_artist TEXT,
  updated_at     TIMESTAMPTZ DEFAULT now()
);
