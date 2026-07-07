-- Database schema for oss-issue-dashboard.
--
-- To set this up on a fresh machine:
--   createdb oss_dashboard
--   psql -d oss_dashboard -f schema.sql

CREATE TABLE IF NOT EXISTS issues (
    id SERIAL PRIMARY KEY,
    repo TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT now(),
    -- Prevents the same issue from being stored twice; fetch_issues.py
    -- relies on this so it can upsert (ON CONFLICT) instead of duplicating.
    UNIQUE (repo, issue_number)
);
