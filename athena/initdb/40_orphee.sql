-- ── Orphée — users ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS orphee_users (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username       TEXT NOT NULL,
  password_hash  TEXT NOT NULL,
  is_admin       BOOLEAN NOT NULL DEFAULT FALSE,
  features       TEXT[] NOT NULL DEFAULT '{}',
  max_jobs       INTEGER NOT NULL DEFAULT 1,
  token_version          INTEGER NOT NULL DEFAULT 0,
  total_videos_created   BIGINT  NOT NULL DEFAULT 0,
  total_duration_seconds BIGINT  NOT NULL DEFAULT 0,
  total_clips_used       BIGINT  NOT NULL DEFAULT 0,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_orphee_users_username ON orphee_users(username);

-- ── Orphée — jobs ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS orphee_jobs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES orphee_users(id) ON DELETE CASCADE,
  title       TEXT,
  status      TEXT NOT NULL DEFAULT 'pending'
                CONSTRAINT chk_orphee_jobs_status
                CHECK (status IN ('pending','downloading','processing','done','failed','cancelled')),
  error             TEXT,
  file_size_bytes   BIGINT,
  duration_seconds  INTEGER,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orphee_jobs_user_id    ON orphee_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_orphee_jobs_created_at ON orphee_jobs(created_at DESC);

-- ── Orphée — metrics ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS orphee_metrics (
  id                     SERIAL PRIMARY KEY,
  total_videos_created   BIGINT NOT NULL DEFAULT 0,
  total_duration_seconds BIGINT NOT NULL DEFAULT 0,
  total_clips_used       BIGINT NOT NULL DEFAULT 0,
  money_earned           NUMERIC(10, 2) NOT NULL DEFAULT 0
);

INSERT INTO orphee_metrics (total_videos_created, total_duration_seconds, total_clips_used)
SELECT 0, 0, 0
WHERE NOT EXISTS (SELECT 1 FROM orphee_metrics);

-- ── Triggers updated_at ───────────────────────────────────────────────────────

DROP TRIGGER IF EXISTS trg_orphee_users_updated ON orphee_users;
CREATE TRIGGER trg_orphee_users_updated
BEFORE UPDATE ON orphee_users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_orphee_jobs_updated ON orphee_jobs;
CREATE TRIGGER trg_orphee_jobs_updated
BEFORE UPDATE ON orphee_jobs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
