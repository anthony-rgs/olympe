CREATE UNIQUE INDEX IF NOT EXISTS ux_artists_name_ci ON artists(artist_name);
CREATE UNIQUE INDEX IF NOT EXISTS ux_albums_title_ci ON albums(title);
CREATE UNIQUE INDEX IF NOT EXISTS ux_titles_name_album_ci ON titles(name, album_id);
