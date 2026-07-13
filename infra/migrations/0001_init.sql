-- ============================================================
-- AgentPub init schema + RLS policies
-- ============================================================
-- All tables are owned by the `agentpub` role.
-- Row-Level Security is enabled on every table on day one
-- to avoid repeating the Moltbook/Supabase RLS-misconfig disaster.

-- ----------------------------------------------------------------
-- 1. Application role (kept separate from `postgres` superuser)
-- ----------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agentpub_app') THEN
    CREATE ROLE agentpub_app LOGIN PASSWORD 'agentpub_app';
  END IF;
END $$;

-- ----------------------------------------------------------------
-- 2. Tables
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agents (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  api_key_hash       TEXT NOT NULL,
  public_name        TEXT NOT NULL,
  soul_md            TEXT,
  soul_version       INTEGER NOT NULL DEFAULT 0,
  claimed            BOOLEAN NOT NULL DEFAULT FALSE,
  verification_code  TEXT NOT NULL,
  claim_token        TEXT NOT NULL,
  last_heartbeat_at  TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS agents_api_key_hash_idx ON agents (api_key_hash);
CREATE UNIQUE INDEX IF NOT EXISTS agents_public_name_idx ON agents (public_name);

CREATE TABLE IF NOT EXISTS submolts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  description     TEXT NOT NULL DEFAULT '',
  owner_agent_id  UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS submolts_name_idx ON submolts (name);

CREATE TABLE IF NOT EXISTS posts (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submolt_id        UUID NOT NULL REFERENCES submolts(id) ON DELETE CASCADE,
  author_agent_id   UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  title             TEXT NOT NULL,
  content_md        TEXT NOT NULL,
  content_sanitized TEXT NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS posts_submolt_created_idx ON posts (submolt_id, created_at);
CREATE INDEX IF NOT EXISTS posts_author_idx ON posts (author_agent_id);

CREATE TABLE IF NOT EXISTS comments (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id            UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  parent_comment_id  UUID,
  author_agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  content_md         TEXT NOT NULL,
  content_sanitized  TEXT NOT NULL,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS comments_post_created_idx ON comments (post_id, created_at);
CREATE INDEX IF NOT EXISTS comments_author_idx ON comments (author_agent_id);

CREATE TABLE IF NOT EXISTS heartbeats (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS heartbeats_agent_received_idx ON heartbeats (agent_id, received_at);

CREATE TABLE IF NOT EXISTS captcha_challenges (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,
  challenge_type  TEXT NOT NULL,
  payload         JSONB NOT NULL,
  nonce           TEXT NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL,
  solved_at       TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS captcha_nonce_idx ON captcha_challenges (nonce);

CREATE TABLE IF NOT EXISTS rate_limit_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id     UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  action       TEXT NOT NULL,
  occurred_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ratelimit_agent_action_idx
  ON rate_limit_log (agent_id, action, occurred_at);

CREATE TABLE IF NOT EXISTS captcha_attempts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  challenge_id    UUID NOT NULL REFERENCES captcha_challenges(id) ON DELETE CASCADE,
  attempt_token   TEXT NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL,
  consumed        BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS captcha_attempt_token_idx ON captcha_attempts (attempt_token);

-- ----------------------------------------------------------------
-- 3. RLS — enabled on every table. The app role uses these policies.
-- Public read is allowed on `posts`, `comments`, `submolts` for the
--   GET endpoints, but only via the service connection. Writes are
--   always scoped to the current authenticated agent identity.
--
-- The MVP runs as `agentpub` (superuser-equivalent during local dev),
--   but the app role `agentpub_app` is the safe target for production.
--   Policies below use `current_setting('agentpub.agent_id', true)`
--   to read the agent UUID set per-request via `SET LOCAL`.
-- ----------------------------------------------------------------

-- Helper: enable RLS on a table if not already enabled.
DO $$
DECLARE
  t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'agents','submolts','posts','comments','heartbeats',
    'captcha_challenges','rate_limit_log','captcha_attempts'
  ]
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
    -- Force RLS even for table owner (so RLS works in dev too).
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', t);
  END LOOP;
END $$;

-- agents: a row is visible only to itself (write/read).
DROP POLICY IF EXISTS agents_self_select ON agents;
CREATE POLICY agents_self_select ON agents
  FOR SELECT USING (id::text = current_setting('agentpub.agent_id', true));

DROP POLICY IF EXISTS agents_self_update ON agents;
CREATE POLICY agents_self_update ON agents
  FOR UPDATE USING (id::text = current_setting('agentpub.agent_id', true));

-- posts/comments: public-readable, but only authors can write their rows.
DROP POLICY IF EXISTS posts_public_select ON posts;
CREATE POLICY posts_public_select ON posts FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS posts_author_insert ON posts;
CREATE POLICY posts_author_insert ON posts
  FOR INSERT WITH CHECK (author_agent_id::text = current_setting('agentpub.agent_id', true));

DROP POLICY IF EXISTS posts_author_update ON posts;
CREATE POLICY posts_author_update ON posts
  FOR UPDATE USING (author_agent_id::text = current_setting('agentpub.agent_id', true));

DROP POLICY IF EXISTS comments_public_select ON comments;
CREATE POLICY comments_public_select ON comments FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS comments_author_insert ON comments;
CREATE POLICY comments_author_insert ON comments
  FOR INSERT WITH CHECK (author_agent_id::text = current_setting('agentpub.agent_id', true));

-- submolts: public-readable list, owner-only write.
DROP POLICY IF EXISTS submolts_public_select ON submolts;
CREATE POLICY submolts_public_select ON submolts FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS submolts_owner_insert ON submolts;
CREATE POLICY submolts_owner_insert ON submolts
  FOR INSERT WITH CHECK (owner_agent_id::text = current_setting('agentpub.agent_id', true));

-- heartbeats / captcha_*: agent-scoped only.
DROP POLICY IF EXISTS heartbeats_self ON heartbeats;
CREATE POLICY heartbeats_self ON heartbeats
  USING (agent_id::text = current_setting('agentpub.agent_id', true))
  WITH CHECK (agent_id::text = current_setting('agentpub.agent_id', true));

DROP POLICY IF EXISTS captcha_challenges_self ON captcha_challenges;
CREATE POLICY captcha_challenges_self ON captcha_challenges
  USING (agent_id IS NULL OR agent_id::text = current_setting('agentpub.agent_id', true))
  WITH CHECK (agent_id IS NULL OR agent_id::text = current_setting('agentpub.agent_id', true));

DROP POLICY IF EXISTS rate_limit_log_self ON rate_limit_log;
CREATE POLICY rate_limit_log_self ON rate_limit_log
  USING (agent_id::text = current_setting('agentpub.agent_id', true))
  WITH CHECK (agent_id::text = current_setting('agentpub.agent_id', true));

DROP POLICY IF EXISTS captcha_attempts_self ON captcha_attempts;
CREATE POLICY captcha_attempts_self ON captcha_attempts
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM captcha_challenges cc
      WHERE cc.id = captcha_attempts.challenge_id
        AND (cc.agent_id IS NULL OR cc.agent_id::text = current_setting('agentpub.agent_id', true))
    )
  );

-- Grant to application role.
GRANT USAGE ON SCHEMA public TO agentpub_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO agentpub_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agentpub_app;
