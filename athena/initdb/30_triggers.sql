CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_artists_updated ON artists;
CREATE TRIGGER trg_artists_updated
BEFORE UPDATE ON artists
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_albums_updated ON albums;
CREATE TRIGGER trg_albums_updated
BEFORE UPDATE ON albums
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_titles_updated ON titles;
CREATE TRIGGER trg_titles_updated
BEFORE UPDATE ON titles
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_tracks_meta_updated ON tracks_meta;
CREATE TRIGGER trg_tracks_meta_updated
BEFORE UPDATE ON tracks_meta
FOR EACH ROW EXECUTE FUNCTION set_updated_at();