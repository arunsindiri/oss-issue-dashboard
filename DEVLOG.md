# OSS Issue Dashboard — Development Log

This file is a running, plain-English record of every step taken on this
project, in order, with the exact commands used and why each step mattered.
It gets a new entry every time we make progress — nothing gets left out.

## What this project is

**oss-issue-dashboard** = **OSS** (open source software) + **Issue** (GitHub
issues) + **Dashboard** (the end goal: a web page to browse/track issues
across repos). Right now we've only built the "get the data" half — a script
that pulls issues from GitHub and stores them in a database. The "dashboard"
(the actual browsable web page) hasn't been built yet.

---

## 2026-07-06 — Initial script

Wrote the first version of `fetch_issues.py`. What it did:

1. Sent a request to GitHub's public API for one repo (`facebook/react`) to
   get its list of issues:
   ```python
   url = f"https://api.github.com/repos/{REPO}/issues"
   response = requests.get(url)
   issues = response.json()
   ```
   GitHub replies with JSON (text formatted as nested lists/dictionaries),
   and `.json()` converts that text into Python data we can loop over.

2. Connected to a local Postgres database called `oss_dashboard`:
   ```python
   conn = psycopg2.connect(dbname="oss_dashboard")
   ```
   No password needed because Postgres was set up to trust your own Linux
   user account for local connections.

3. Looped over every issue and inserted it into an `issues` table, skipping
   anything that was actually a pull request (GitHub's issues API lumps
   PRs in with real issues — a PR object has a `"pull_request"` key that a
   real issue doesn't):
   ```python
   if "pull_request" in issue:
       continue
   cur.execute(
       "INSERT INTO issues (repo, issue_number, title, url) VALUES (%s, %s, %s, %s)",
       (REPO, issue["number"], issue["title"], issue["html_url"]),
   )
   ```

4. Called `conn.commit()` at the end — in Postgres, nothing you `INSERT` is
   permanently saved until you commit; this confirms the whole batch at once.

Also created `requirements.txt` listing the Python packages needed
(`requests` to talk to GitHub, `psycopg2-binary` to talk to Postgres) and set
up a `venv/` (a self-contained Python environment) so these packages don't
clash with anything else on the machine.

**Result at this point:** running the script once loaded 7 real issues from
`facebook/react` into the `issues` table.

---

## 2026-07-07 — Turned it into a real git project and pushed to GitHub

You created a new empty repo on GitHub: `git@github.com:arunsindiri/oss-issue-dashboard.git`
(the `git@github.com:...` form means "connect over SSH," which uses your SSH
key instead of a username/password).

Steps taken:

1. **Checked there was no git repo yet:**
   ```
   git status
   ```
   → confirmed with "fatal: not a git repository."

2. **Initialized git** in the project folder:
   ```
   git init
   ```
   This creates a hidden `.git/` folder that tracks every change you make
   from now on.

3. **Renamed the default branch to `main`** (GitHub's standard name; git
   itself still defaults to the older name `master` on this machine):
   ```
   git branch -m main
   ```

4. **Added a `.gitignore` file** listing things git should never track:
   ```
   venv/
   __pycache__/
   *.pyc
   .env
   ```
   We ignore `venv/` because it's a large, machine-specific folder that
   anyone can regenerate from `requirements.txt` — it doesn't belong in
   source control. `.env` is ignored pre-emptively in case secrets
   (API keys, passwords) ever get stored in a file like that.

5. **Staged and committed the existing files:**
   ```
   git add fetch_issues.py requirements.txt .gitignore
   git commit -m "Initial commit: GitHub issue fetcher into Postgres"
   ```
   "Staging" (`git add`) means marking files as ready to be saved in the
   next commit. A "commit" is a permanent snapshot of the project at that
   moment, with a message describing what changed.

6. **Connected the local repo to GitHub:**
   ```
   git remote add origin git@github.com:arunsindiri/oss-issue-dashboard.git
   ```
   "origin" is just the conventional nickname for your main remote copy.

7. **Pushed the commit up to GitHub:**
   ```
   git push -u origin main
   ```
   `-u` tells git to remember that your local `main` branch should sync
   with `origin`'s `main` branch, so future `git push`/`git pull` commands
   don't need the full arguments.

**Result at this point:** the project's code is now backed up and visible
on GitHub, not just sitting on your local machine.

---

## 2026-07-07 — Fixed duplicate-insert risk and added multi-repo support

**Problem found:** the `issues` table had no rule stopping the same issue
from being inserted twice. Running `fetch_issues.py` a second time would
have added every issue again as a duplicate row, since plain `INSERT`
doesn't know an issue was already saved.

1. **Checked for existing duplicates before adding a safety rule** (adding
   the rule would fail if duplicates already existed):
   ```
   psql -d oss_dashboard -c "SELECT repo, issue_number, count(*) FROM issues GROUP BY repo, issue_number HAVING count(*) > 1;"
   ```
   → zero rows returned, so it was safe to proceed.

2. **Added a uniqueness rule** to the database so it physically cannot
   contain two rows with the same `repo` + `issue_number` combination:
   ```
   ALTER TABLE issues ADD CONSTRAINT issues_repo_number_unique UNIQUE (repo, issue_number);
   ```

3. **Rewrote `fetch_issues.py`:**
   - Changed `REPO = "facebook/react"` (one repo) into a `REPOS = [...]`
     list containing `facebook/react`, `vuejs/vue`, and `microsoft/vscode`,
     and wrapped the whole fetch in a loop so it runs once per repo.
   - Changed the plain `INSERT` into an **upsert** — insert if the row is
     new, or update it in place if it already exists — using Postgres's
     `ON CONFLICT` clause:
     ```sql
     INSERT INTO issues (repo, issue_number, title, url)
     VALUES (%s, %s, %s, %s)
     ON CONFLICT (repo, issue_number)
     DO UPDATE SET title = EXCLUDED.title, url = EXCLUDED.url
     ```
     This only works *because* of the uniqueness rule added in step 2 —
     `ON CONFLICT` needs to know which combination of columns counts as
     "the same row."

4. **Tested it by running the script twice in a row:**
   ```
   python fetch_issues.py
   ```
   First run added new issues from all three repos. Second run reported
   the same totals but the row counts in the table didn't increase —
   proving the upsert logic works and re-running the script is now safe.

5. **Committed and pushed the change:**
   ```
   git add fetch_issues.py
   git commit -m "Support multiple repos and upsert instead of plain insert"
   git push
   ```

**Known gap left open:** the uniqueness rule from step 2 was applied
directly with `psql`, so it only exists in your local database — it isn't
written down anywhere in the repo. If you set this project up on a new
machine today, that step would be missing. Fixing this (e.g. a
`schema.sql` file) is a candidate for the next entry in this log.

---

## 2026-07-07 — Added schema.sql to close the reproducibility gap

**Problem being fixed:** the previous entry's uniqueness rule was applied
directly with `psql` against the live database — nothing in the repo
recorded the table structure, so a fresh machine had no way to reproduce it.

1. **Wrote `schema.sql`**, a single file that creates the `issues` table
   from nothing, including the same unique constraint added earlier:
   ```sql
   CREATE TABLE IF NOT EXISTS issues (
       id SERIAL PRIMARY KEY,
       repo TEXT NOT NULL,
       issue_number INTEGER NOT NULL,
       title TEXT NOT NULL,
       url TEXT NOT NULL,
       fetched_at TIMESTAMP DEFAULT now(),
       UNIQUE (repo, issue_number)
   );
   ```
   `SERIAL PRIMARY KEY` means "auto-incrementing whole number, and no two
   rows can share one" — this is what Postgres was already doing for `id`
   behind the scenes; writing it explicitly means a new setup gets the
   same behavior.

2. **Tested it without touching the real data.** Couldn't create a whole
   new throwaway database (the Postgres user here isn't allowed to run
   `CREATE DATABASE`), so instead created a temporary *schema* — think of
   it as a separate folder inside the same database — ran `schema.sql`
   inside it, confirmed the resulting table matched the real one exactly
   (same columns, same primary key, same unique constraint), then deleted
   the temporary schema:
   ```
   psql -d oss_dashboard <<'EOF'
   CREATE SCHEMA test_schema;
   SET search_path TO test_schema;
   \i schema.sql
   \d test_schema.issues
   DROP SCHEMA test_schema CASCADE;
   EOF
   ```

3. **Committed and pushed:**
   ```
   git add schema.sql
   git commit -m "Add schema.sql to reproduce the database from scratch"
   git push
   ```

**Result at this point:** anyone (including future-you on a new machine)
can now run `createdb oss_dashboard && psql -d oss_dashboard -f schema.sql`
and get a database that behaves identically to the one already in use.

---

## What's next (not started yet)

- The dashboard itself — a web page that reads from the `issues` table and
  displays them, instead of only looking at raw rows via `psql`.
