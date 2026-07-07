from flask import Flask, render_template, request, jsonify
import psycopg2

app = Flask(__name__)


def get_repos(cur):
    # The dropdown needs every repo we track, regardless of the current
    # filters, so it's a separate query from the (possibly filtered) list.
    cur.execute("SELECT DISTINCT repo FROM issues ORDER BY repo")
    return [row[0] for row in cur.fetchall()]


def get_issues(cur, q, repo):
    where_clauses = []
    params = []

    if q:
        # ILIKE is Postgres's case-insensitive LIKE; %...% matches the
        # keyword anywhere in the title.
        where_clauses.append("title ILIKE %s")
        params.append(f"%{q}%")

    if repo:
        where_clauses.append("repo = %s")
        params.append(repo)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # Newest-fetched issues first, so refreshing after a fetch shows changes.
    cur.execute(
        f"""
        SELECT repo, issue_number, title, url
        FROM issues
        {where_sql}
        ORDER BY repo, issue_number DESC
        """,
        params,
    )

    return [
        {"repo": r, "number": number, "title": title, "url": url}
        for r, number, title, url in cur.fetchall()
    ]


@app.route("/")
def index():
    # Search box (?q=) and repo dropdown (?repo=), both optional.
    q = request.args.get("q", "").strip()
    repo = request.args.get("repo", "").strip()

    # Same local-user connection style used in fetch_issues.py.
    conn = psycopg2.connect(dbname="oss_dashboard")
    cur = conn.cursor()

    repos = get_repos(cur)
    issues = get_issues(cur, q, repo)

    cur.close()
    conn.close()

    return render_template("index.html", issues=issues, repos=repos, q=q, selected_repo=repo)


@app.route("/api/issues")
def api_issues():
    # JSON version of the same filtered query, used by static/app.js so the
    # search box and repo dropdown can update the table live without a full
    # page reload. Always the source of truth for what matches a filter —
    # the browser never has to guess from rows already on the page.
    q = request.args.get("q", "").strip()
    repo = request.args.get("repo", "").strip()

    conn = psycopg2.connect(dbname="oss_dashboard")
    cur = conn.cursor()

    issues = get_issues(cur, q, repo)

    cur.close()
    conn.close()

    return jsonify(issues=issues)


if __name__ == "__main__":
    # 0.0.0.0 (not just 127.0.0.1) so it's reachable from the Windows
    # browser via WSL2's networking, not only from inside WSL itself.
    app.run(host="0.0.0.0", debug=True)
