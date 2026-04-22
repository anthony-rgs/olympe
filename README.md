# Olympe

**Olympe** is a modular Docker stack to scrape, ingest, store, and serve Spotify “Billions Club” data (and related datasets). \
It is composed of small services wired together with `docker compose`.

> **Part of the Olympe Stack**
>
> - Scraper (separate repo): **Artemis**
> - Ingestion to DB: **Owl**
> - Script runner: **Heracles**
> - Cron: **Sisyphe**
> - API: **Hermes**
> - Database: **Athena** (Postgres)
> - Reverse proxy & TLS: **Caddy**
> - Video generation API: **Orphée**
> - Front‑end (separate repo): **Elysium** — https://spotify-billions.club

## 🧩 Services at a glance

- **caddy** — _Reverse proxy with automatic HTTPS_  
  Serves the site and routes to the API according to `infra/Caddyfile`.

- **artemis** — _Scraper / data collector_  
  Fetches Spotify data and writes JSON files into `./artemis/collections` (mounted as `/app/collections`).  
  Its code is shared via the named volume `artemis-code`.

- **athena** — _Postgres 16_  
  Persistent storage for structured data. Auto‑init via `./athena/initdb`.  
  Data directory persisted under `./athena/pgdata`.

- **owl** — _Ingestion into the DB_  
  Reads JSON produced by Artemis (`/data/collections`) and writes to Postgres (via `DATABASE_URL`).  
  Key env: `TRACKS_PATH`, `ARTISTS_PATH`.

- **heracles** — _Script manager_  
  Centralizes and runs maintenance/scrape/ingestion scripts.  
  Shares Artemis code (`artemis-code`) and can `docker exec` into sibling services.

- **hermes** — _API backend_  
  Exposes data from the DB and/or JSON files. Env: `DATABASE_URL`, `CORS_ORIGINS`, `TRACKS_PATH`, `ARTISTS_PATH`.

- **sisyphe** — _Scheduler (cron/automation)_  
  Periodically triggers scripts (often via `docker exec` on Heracles).  
  Needs access to Docker socket: `/var/run/docker.sock`.

- **orphée** — _Automated video generation API_  
  Generates short-form 9:16 videos from music clips. Downloads source videos via `yt-dlp`, cuts clips, and assembles the final render with `ffmpeg`. Exposes a JWT-authenticated REST API with SSE streaming for job status.  
  Env: `ANTHROPIC_API_KEY`, `JWT_SECRET`, `JWT_EXPIRE_HOURS`, `CORS_ORIGINS`, `STORAGE_ROOT`.  
  Requires a `cookie.txt` (Netscape format) mounted at `/storage/cookies.txt` for YouTube authentication.

---

## 🚀 Quick start

### 1) Prerequisites

- Docker & Docker Compose
- A domain if you plan to expose services publicly (for Caddy + HTTPS)

### 2) Environment

Create a `.env` file at the repo root based on the .env.example:

```bash
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
DATABASE_URL=
CORS_ORIGINS=
```

### 3) Reverse proxy

Adjust `infra/Caddyfile` to match your domains and routes.

### 4) Launch

```bash
docker compose up -d --build
docker compose ps
```

### 5) Useful logs

```bash
docker compose logs -f <service name>
```

---

## 📁 Volumes & folders

- **Artemis JSON (local):** `./artemis/collections` (mounted read‑only or read‑write by several services)
- **Postgres data:** `./athena/pgdata`
- **Postgres init scripts:** `./athena/initdb` (executed on first start)
- **Shared Artemis code:** named volume `artemis-code`
- **Caddy:** configuration under `./infra/Caddyfile`

---

## 🔧 Common commands

**Run a manual scrape in Artemis**

```bash
docker compose exec artemis bash -lc 'python -u /app/run_scrape.py'
```

**Manual ingestion with Owl**

```bash
docker compose exec owl bash -lc 'python -u /app/ingest.py'
```

**Trigger via Heracles**

```bash
docker compose exec heracles python3 /app/run_billion_club.py
```

**Inspect Sisyphe cron**

```bash
docker compose exec sisyphe crontab -l
docker compose logs -f sisyphe
```

**Backup the DB**

```bash
docker compose exec athena pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

---

## 🏛️ Service names

- Scraper — **Artemis**: goddess of the hunt and the wilderness → “hunts” the data
- Database — **Athena**: goddess of wisdom and strategic warfare → centralized knowledge base
- Ingestion to DB — **Owl**: Athena’s owl, symbol of insight → ferries data into Athena
- Script runner — **Heracles**: hero of the Twelve Labors → executes heavy tasks
- Cron — **Sisyphe**: condemned to repeat the same act endlessly → recurring scheduling
- API — **Hermes**: messenger of the gods, deity of travel and exchange → delivers data to the outside world
- Video generation — **Orphée**: poet and musician of Greek mythology, enchanting all with his music → crafts videos from raw clips
- Website — **Elysium**: realm of heroes / virtuous souls → the showcase for the “best” data

---

## Links

- Front‑end: **Elysium** — https://spotify-billions.club
- Front‑end code: [Elysium](https://github.com/anthony-rgs/elysium)
- Scraper: [Artemis](https://github.com/anthony-rgs/artemis)
