import requests
import psycopg2

# This is the repo we're asking GitHub about.
# Format: "owner/repo" — e.g. the React library lives at github.com/facebook/react
REPO = "facebook/react"

# This is the web address (API endpoint) GitHub gives us to ask for issues.
url = f"https://api.github.com/repos/{REPO}/issues"

# This actually sends the request over the internet and waits for GitHub's reply.
response = requests.get(url)

# GitHub sends the reply back as JSON (a common text format for data).
# .json() turns that text into a Python list of dictionaries we can use.
issues = response.json()

print(f"Found {len(issues)} issues in {REPO}\n")

# This opens a connection to our local Postgres database.
# No host/password needed — connecting as your own Linux user is enough locally.
conn = psycopg2.connect(dbname="oss_dashboard")
cur = conn.cursor()

saved_count = 0

for issue in issues:
    # GitHub's "issues" endpoint also includes pull requests.
    # Real issues don't have a "pull_request" key, so we skip anything that does.
    if "pull_request" in issue:
        continue

    cur.execute(
        """
        INSERT INTO issues (repo, issue_number, title, url)
        VALUES (%s, %s, %s, %s)
        """,
        (REPO, issue["number"], issue["title"], issue["html_url"]),
    )
    saved_count += 1

# Nothing is actually written to the database until we "commit" — this
# saves all the INSERTs above as one confirmed batch.
conn.commit()

cur.close()
conn.close()

print(f"Saved {saved_count} issues into Postgres.")
