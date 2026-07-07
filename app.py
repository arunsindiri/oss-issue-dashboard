from flask import Flask, render_template
import psycopg2

app = Flask(__name__)


@app.route("/")
def index():
    # Same local-user connection style used in fetch_issues.py.
    conn = psycopg2.connect(dbname="oss_dashboard")
    cur = conn.cursor()

    # Newest-fetched issues first, so refreshing after a fetch shows changes.
    cur.execute(
        """
        SELECT repo, issue_number, title, url
        FROM issues
        ORDER BY repo, issue_number DESC
        """
    )
    rows = cur.fetchall()

    cur.close()
    conn.close()

    issues = [
        {"repo": repo, "number": number, "title": title, "url": url}
        for repo, number, title, url in rows
    ]

    return render_template("index.html", issues=issues)


if __name__ == "__main__":
    app.run(debug=True)
