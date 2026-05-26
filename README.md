# Repo Health Score

**A unified letter grade for your GitHub repository health.**

See at a glance how healthy your repos are across dependencies, CI/CD, PRs, issues, community, and documentation. Get a single score with specific recommendations for what needs to be fixed first.

[![PyPI version](https://img.shields.io/pypi/v/repo-health-score.svg)](https://pypi.org/project/repo-health-score/)
[![PyPI downloads](https://img.shields.io/pypi/dm/repo-health-score.svg)](https://pypi.org/project/repo-health-score/)
[![CI status](https://github.com/CatfishGG/repo-health-score/actions/workflows/tests.yml/badge.svg)](https://github.com/CatfishGG/repo-health-score/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Why

Most developers have more than a handful of repositories. Over time, things rot silently: dependencies go out of date, PRs go stale, CI breaks and you forget, issues pile up without responses.

You only find out when something breaks badly or you need to use that repo again.

**Repo Health Score** gives you a single letter grade (A-F) across six maintenance dimensions, so you can spot the problems before they become crises.

---

## Installation

```bash
pip install repo-health-score
```

Requires Python 3.10 or later.

---

## Quick Start

```bash
# Set your GitHub token once
export GITHUB_TOKEN=ghp_your_token_here

# Score a single repo
repo-health-score owner/repo

# Score all your repos
repo-health-score --all-repos

# Score a specific user or org
repo-health-score --user some-org
```

That's it. You'll get a letter grade and specific recommendations for each repo.

---

## What gets scored

| Dimension | Weight | What it measures |
|---|---|---|
| **Dependencies** | 25% | Security vulnerabilities, outdated packages, lock file presence |
| **CI/CD** | 20% | Build success rate, workflow health, average build duration |
| **Pull Requests** | 20% | PR age, stale PRs, unreviewed PRs, review turnaround |
| **Issues** | 15% | Issue age, stale issues, no-response issues |
| **Community** | 10% | License, contributing guidelines, issue/PR templates |
| **Documentation** | 10% | README quality, installation guide, usage examples |

Each dimension is scored 0-100, then weighted and combined into a single letter grade:

- **A** (90-100): Excellent
- **B** (80-89): Good
- **C** (70-79): Needs attention
- **D** (60-69): Needs significant work
- **F** (Below 60): Critical

---

## Output formats

**Summary (default)**
```
============================================================
REPO HEALTH SCORES
============================================================

B [84.0/100] owner/some-repo
  -> Update 2 outdated dependencies
  -> Close 3 stale pull requests

A [91.5/100] owner/healthy-repo

------------------------------------------------------------
Scanned 12 repositories
============================================================
```

**Table**
```bash
repo-health-score --all-repos --output table
```
```
Repo                                     Score   Letter
--------------------------------------------------------------
owner/healthy-repo                       91.5       A
owner/another-good-repo                  85.0       B
owner/needs-attention                    73.5       C
```

**JSON** (for integrations)
```bash
repo-health-score owner/repo --output json
```
```json
{
  "owner": "owner",
  "repo": "some-repo",
  "overall_score": 84.0,
  "overall_letter": "B",
  "dimensions": [
    {
      "name": "dependencies",
      "score": 75.0,
      "weight": 0.25,
      "letter": "C",
      "details": { "outdated_count": 2 }
    }
  ],
  "recommendations": [
    "Update 2 outdated dependencies"
  ]
}
```

**Save to file**
```bash
repo-health-score --all-repos --json-output health-report.json
```

---

## Custom scoring weights

If you care more about security than docs, or want to prioritise CI/CD over everything else:

```bash
repo-health-score owner/repo --weights '{
  "dependencies": 0.4,
  "ci_cd": 0.25,
  "pull_requests": 0.15,
  "issues": 0.1,
  "community": 0.05,
  "documentation": 0.05
}'
```

Weights must sum to 1.0.

---

## Badge generation

Embed a health score badge directly in your repo's README.

**Direct URL:**
```
https://repo-health-score.deno.dev/badge/{owner}/{repo}.svg?score={score}&letter={grade}
```

**Example markdown:**
```md
[![Repo Health Score](https://repo-health-score.deno.dev/badge/owner/repo.svg?score=84&letter=B)](https://github.com/owner/repo)
```

**Colors:**
- A → green (#4c1)
- B → light green (#9c6)
- C → yellow (#dfb317)
- D → orange (#d9730d)
- F → red (#e05c44)

You can also run the badge generator locally via the web server.

---

## Web server

Run a local API server for score history tracking and the React dashboard:

```bash
# Start the API server
repo-health-score serve --host 127.0.0.1 --port 8000
```

The server exposes:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/repos/{owner}/{repo}/score?store=true` | GET | Scan and get current score |
| `/repos/{owner}/{repo}/history?days=30` | GET | Score history |
| `/repos/{owner}/{repo}/history/latest` | GET | Most recent score |
| `/repos/{owner}/{repo}/scan` | POST | Trigger new scan |
| `/badge/{owner}/{repo}.svg?score=X&letter=Y` | GET | SVG badge |

Set `GITHUB_TOKEN` as a header or environment variable:
```bash
Authorization: Bearer ghp_your_token_here
```

---

## React dashboard

A dashboard UI is available at `dashboard/`. To run it:

```bash
cd dashboard
npm install
npm run dev
```

Set `VITE_API_URL` to point to your running API server (default: `http://localhost:8000`).

Features:
- Repo cards sorted by health score
- Click through to see score breakdown by dimension
- Score history line chart (last 30 days)
- Badge with copy-to-clipboard markdown for embedding

---

## Authentication

### Personal Access Token (PAT)

The fastest way to get started. Requires a GitHub PAT with `repo` scope.

```bash
export GITHUB_TOKEN=ghp_your_token_here
repo-health-score owner/repo
```

Create a token at: https://github.com/settings/tokens

### GitHub App

For organisations needing fine-grained repo access control, use the GitHub App authentication flow. This avoids PATs and uses per-installation tokens with proper permission scoping.

#### Registering a GitHub App

1. Go to **Settings > Developer settings > GitHub Apps > New GitHub App**
   https://github.com/settings/apps/new

2. Fill in the basics:
   - **GitHub App name**: `repo-health-score` (must be unique across GitHub)
   - **Homepage URL**: `https://github.com/CatfishGG/repo-health-score`

3. **Callback URL**: Set to your server's OAuth callback:
   ```
   http://localhost:8484/oauth/callback
   ```
   For production, use your public URL.

4. **Post-installation callback URL**: Same as the callback URL.

5. **Permissions** (under *Permissions* section):

   | Permission | Access |
   |---|---|
   | Contents | Read-only |
   | Issues | Read-only |
   | Metadata | Read-only |
   | Pull requests | Read-only |
   | Actions | Read-only |
   | Checks | Read-only |
   | Dependabot alerts | Read-only |
   | Repository projects | Read-only |

6. **Subscribe to events**:
   - Push
   - Pull request
   - Installation / InstallationRepositories

7. Where can this GitHub App be installed?
   - Select **Any account** if you want users to install it on their own accounts
   - Select **Only on this account** for organisation-only use

8. Click **Create GitHub App**.

9. On the resulting page:
   - Copy the **App ID**: set as `GITHUB_APP_APP_ID`
   - Copy the **Client ID**: set as `GITHUB_APP_CLIENT_ID`
   - Click **Generate a new private key**. Download the `.pem` file and set its contents as `GITHUB_APP_PRIVATE_KEY`
   - Copy the **Client secret**: set as `GITHUB_APP_CLIENT_SECRET`

#### Environment variables

```bash
# Required
export GITHUB_APP_CLIENT_ID=Iv1.xxxxxxxxxxxx
export GITHUB_APP_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export GITHUB_APP_APP_ID=123456
# Private key: copy the entire PEM file contents as a single-line string
# (newlines replaced with \n)
export GITHUB_APP_PRIVATE_KEY="$(cat app-name.private-key.pem | tr '\n' ' ')"

# Optional
# export GITHUB_APP_REDIRECT_URI=http://localhost:8484/oauth/callback
# export GITHUB_APP_WEBHOOK_SECRET=your_webhook_secret
# export GITHUB_APP_PORT=8484
```

Or pass them directly in the environment before starting the server.

#### Starting the server

```bash
# First, install the package (or use the venv)
source .venv/bin/activate

# Start the OAuth/webhook server
repo-health-score serve
# or
python -m repo_health_score.github_app.app
```

The server will print the URL to open for the OAuth installation flow.


#### Running the CLI with GitHub App auth

```bash
# After authenticating via the web server,
# use --app to scan repos via GitHub App
repo-health-score owner/repo --app

# Scan all repos
repo-health-score --all-repos --app
```

#### How the flow works

1. `repo-health-score serve` starts the FastAPI server at `localhost:8484`
2. Open `http://localhost:8484/install` - this redirects to GitHub to authorise the App
3. GitHub redirects to `/oauth/callback` with an authorization code
4. The server exchanges the code for an access token and stores it at `~/.repo_health_score/app_tokens.json`
5. The CLI reads the stored token automatically on subsequent runs with `--app`

6. When scanning a repo, the server uses an **installation token** scoped to that specific repo installation

#### Notes for production

- Use a reverse proxy (nginx, Caddy) with HTTPS in front of the FastAPI server
- Set `GITHUB_APP_WEBHOOK_SECRET` to the webhook secret from your App settings and enable signature validation in `routes.py`
- The token store path can be changed via `GITHUB_APP_TOKEN_STORE`
- The OAuth callback URL must be publicly reachable for GitHub to redirect back to it


---

## All options

```
usage: repo-health-score [-h] [--app] [--token TOKEN] [--all-repos]
                         [--user USER] [--output {json,table,summary}]
                         [--json-output PATH] [--weights JSON]
                         [--exclude REPO [REPO ...]]
                         [--host HOST] [--port PORT]
                         [repo] [serve|scan]

Score the health of GitHub repositories.


positional arguments:
  repo                  Repository in format 'owner/repo'
  command               'serve' starts the GitHub App OAuth/webhook server

optional arguments:
  --app                  Use GitHub App authentication (requires server running)
  --token, -t            GitHub PAT (or set GITHUB_TOKEN env var)
  --all-repos            Scan all repositories for the authenticated user
  --user, -u             Scan all repos for a specific user/org
  --output               Output format: json, table, or summary (default)
  --json-output          Write JSON output to a file
  --weights              Custom dimension weights as JSON
  --exclude              Repos to exclude from --all-repos or --user scans
  --host                 Web server host (default: 127.0.0.1)
  --port                 Web server port (default: 8000)
```

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. The project follows [Conventional Commits](https://www.conventionalcommits.org/).

---

## License

MIT - see [LICENSE](LICENSE).
