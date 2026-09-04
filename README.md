# Rally ↔ GitLab Bridge v0.2.0

Selective Rally → GitLab migration and controlled synchronization for a squad.

## Browser SSO POC mode

This release adds a POC mode for Rally users who sign in with company SSO but cannot create Rally API keys or OAuth clients.

**Important:** the bridge does not copy or store `iceSessionId`, Rally cookies, SSO tokens, or browser credentials. A helper script runs on the already-authenticated Rally page, reads the selected work items using that page's own browser session, and downloads a JSON snapshot. The local bridge consumes only that snapshot.

Browser-session mode is intentionally **read-only toward Rally** in v0.2.0. Rally → GitLab preview/import/reconciliation can use a refreshed snapshot. GitLab → Rally automated writes remain disabled for this POC.

## Install / upgrade

```bash
cd /path/to/rally-gitlab-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

If you already have the app installed, from the new v0.2.0 folder simply run:

```bash
pip install -e .
```

## Configure browser-session mode

Copy the example configuration:

```bash
cp .env.example .env
```

The Rally section should contain:

```dotenv
RALLY_AUTH_MODE=browser_snapshot
RALLY_SNAPSHOT_FILE=data/rally_snapshot.json
RALLY_BASE_URL=https://rally1.rallydev.com
RALLY_API_KEY=
```

`RALLY_API_KEY` remains blank.

You can leave Workspace/Project OIDs blank for this mode. Squad filtering is performed after the snapshot is loaded. For example:

```dotenv
RALLY_SQUAD_FIELD=Project
RALLY_SQUAD_VALUE=My Squad
RALLY_QUARTER_FIELD=c_Quarter
```

Only set `RALLY_SQUAD_VALUE` when you know the exact Rally Project/Squad name you want to include. Leaving it blank disables squad filtering.

## Run

```bash
uvicorn app.main:app --reload
```

Open:

- Dashboard: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/health`
- Browser helper instructions: `http://127.0.0.1:8000/rally/browser-helper`

## Create a Rally snapshot

1. Open the bridge dashboard and choose **Create snapshot from logged-in Rally**.
2. Download `rally-browser-helper.js`.
3. Open Rally normally and sign in through company SSO.
4. Open browser Developer Tools → Console on the Rally page.
5. Open the downloaded JS file, copy its contents, paste it into the Rally page console, and press Enter.
6. Choose `feature`, `quarter`, or `story` and enter the Rally identifier/value.
7. The helper downloads a JSON file. No Rally item is changed.
8. Return to the local dashboard and upload that JSON file.

After upload, the dashboard shows the snapshot scope and counts.

## Preview from the snapshot

For a feature snapshot such as `F1234`:

```bash
rally-gitlab-bridge preview feature F1234
```

For a story:

```bash
rally-gitlab-bridge preview story US1234
```

For a quarter:

```bash
rally-gitlab-bridge preview quarter Q4-2026
```

Preview does not create anything in GitLab.

## GitLab

Only configure GitLab after Rally snapshot preview is working. Use a test GitLab project first.

```dotenv
GITLAB_BASE_URL=https://gitlab.example.com
GITLAB_TOKEN=...
GITLAB_PROJECT_ID=123
GITLAB_PROJECT_PATH=group/project
```

Then import one small feature/story first.

## Tests

```bash
pytest
```
