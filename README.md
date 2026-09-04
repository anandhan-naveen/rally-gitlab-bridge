# Rally ↔ GitLab Bridge v0.3.0

Selective Rally → GitLab migration and controlled synchronization for a squad, rebuilt as a **Node.js / JavaScript application**. No Python installation is required.

## Why this exists

Rally remains the programme/cross-squad planning source while GitLab is used for squad execution. The bridge only synchronizes the selected overlap instead of attempting a full migration.

## Stack

- Node.js 20+
- JavaScript (ES modules)
- Express
- SQLite via `better-sqlite3`
- Commander CLI
- Native `fetch` for GitLab REST calls
- Browser-side Rally snapshot helper for company SSO environments

## Rally browser SSO mode

The bridge does **not** copy or store `iceSessionId`, Rally cookies, SSO tokens, localStorage values, or browser credentials. The helper runs on an already-authenticated Rally page and uses that browser page's existing session to read selected work items. It downloads only a JSON snapshot, which is then uploaded to the local bridge.

Rally access remains read-only in this POC. GitLab → Rally changes are reported as proposed Rally updates rather than being written automatically.

## Install

Check that Node is available:

```bash
node --version
npm --version
```

Node.js 20 or newer is recommended.

Then:

```bash
git clone https://github.com/anandhan-naveen/rally-gitlab-bridge.git
cd rally-gitlab-bridge
npm install
cp .env.example .env
npm run dev
```

Open `http://127.0.0.1:8000`.

## Create a Rally snapshot

1. Start the bridge and open the dashboard.
2. Choose **Create snapshot from logged-in Rally**.
3. Download `rally-browser-helper.js`.
4. Open Rally and sign in normally with company SSO.
5. Open Developer Tools → Console on the Rally page.
6. Paste the helper contents into the Rally console and run it.
7. Choose `story`, `feature`, or `quarter` and enter the value.
8. Rally downloads a JSON snapshot. No Rally work item is changed.
9. Upload the JSON file on the local bridge dashboard.

The helper deliberately avoids requesting the quarter custom field for story/feature snapshots, so subscriptions without `c_Quarter` can still use those scopes.

## CLI

Preview without creating anything:

```bash
npm run bridge -- preview story US1234
npm run bridge -- preview feature F1234
npm run bridge -- preview quarter Q4-2026
```

Dry-run an import:

```bash
npm run bridge -- import feature F1234 --dry-run
```

Import:

```bash
npm run bridge -- import feature F1234
```

Reconcile Rally-owned fields into GitLab:

```bash
npm run bridge -- sync feature F1234 --dry-run
npm run bridge -- sync feature F1234
```

Status:

```bash
npm run bridge -- status
```

## GitLab configuration

Start with a test project.

```dotenv
GITLAB_BASE_URL=https://gitlab.example.com
GITLAB_TOKEN=
GITLAB_PROJECT_ID=123
GITLAB_PROJECT_PATH=group/project
```

The token should be kept only in your local `.env`; `.env` is ignored by Git.

## Current behavior

- Selective scopes: story, feature, quarter, or all snapshot stories
- Local squad filtering
- Preview and dry-run support
- Idempotent import using durable Rally ObjectID ↔ GitLab IID mappings
- Rally stories become GitLab issues
- Rally tasks are created as GitLab issues labelled `source::rally-task` and reference their parent story issue
- Rally-owned title/description reconciliation into GitLab
- GitLab-owned state/assignee changes are surfaced as proposed Rally updates in browser-snapshot mode
- Local web dashboard and CLI

## Field ownership model

The intended model is deliberately asymmetric:

- **Rally master:** title, description, quarter, feature, dependencies, squad/team
- **GitLab master:** execution state, assignee, estimates

This avoids an unsafe generic bidirectional sync.

## Development

```bash
npm run dev
npm test
```

Health endpoint: `http://127.0.0.1:8000/health`
