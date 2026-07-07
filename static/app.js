// Progressive enhancement: the filter form above already works with no JS
// at all (it's a plain GET to "/", handled server-side in app.py). Once
// this script runs, it takes over so filtering happens live against
// /api/issues instead of doing a full page reload.
document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form.filters");
    if (!form) return;

    const qInput = form.querySelector('input[name="q"]');
    const repoSelect = form.querySelector('select[name="repo"]');
    const tbody = document.getElementById("issues-body");
    const countEl = document.getElementById("count");

    let debounceTimer = null;

    function renderRows(issues) {
        tbody.textContent = "";

        if (issues.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.className = "no-results";
            cell.colSpan = 3;
            cell.textContent = "No matching issues.";
            row.appendChild(cell);
            tbody.appendChild(row);
            return;
        }

        for (const issue of issues) {
            const row = document.createElement("tr");

            const repoCell = document.createElement("td");
            repoCell.className = "repo";
            repoCell.textContent = issue.repo;

            const numberCell = document.createElement("td");
            numberCell.textContent = issue.number;

            const titleCell = document.createElement("td");
            const link = document.createElement("a");
            link.className = "title";
            link.href = issue.url;
            link.target = "_blank";
            link.rel = "noopener";
            // textContent (not innerHTML) so a title can never inject markup.
            link.textContent = issue.title;
            titleCell.appendChild(link);

            row.append(repoCell, numberCell, titleCell);
            tbody.appendChild(row);
        }
    }

    async function applyFilter() {
        const params = new URLSearchParams();
        const q = qInput.value.trim();
        const repo = repoSelect.value;
        if (q) params.set("q", q);
        if (repo) params.set("repo", repo);

        const response = await fetch(`/api/issues?${params.toString()}`);
        const data = await response.json();

        renderRows(data.issues);
        const count = data.issues.length;
        countEl.textContent = `${count} issue${count === 1 ? "" : "s"} tracked`;
    }

    // Debounce the search box so we're not firing a request per keystroke;
    // the repo dropdown only fires on an actual change, so no debounce needed.
    qInput.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(applyFilter, 200);
    });
    repoSelect.addEventListener("change", applyFilter);

    // JS is filtering live now, so the form's own full-page-reload submit
    // is no longer needed.
    form.addEventListener("submit", (event) => event.preventDefault());
});
