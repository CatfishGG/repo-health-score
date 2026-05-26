# Repo Health Score

**A unified letter grade for your GitHub repository health.**

See at a glance how healthy your repos are across dependencies, CI/CD, PRs, issues, community, and documentation. Get a single score with specific recommendations for what to fix first.

[![PyPI version](https://img.shields.io/pypi/v/repo-health-score.svg)](https://pypi.org/project/repo-health-score/)
[![PyPI downloads](https://img.shields.io/pypi/dm/repo-health-score.svg)](https://pypi.org/project/repo-health-score/)
[![CI status](https://github.com/CatfishGG/repo-health-score/actions/workflows/tests.yml/badge.svg)](https://github.com/CatfishGG/repo-health-score/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Why

Most developers have more than a handful of repositories. Over time, things rot silently — dependencies go out of date, PRs go stale, CI breaks and you forget, issues pile up without responses.

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

- **A** — 90-100: Excellent
- **B** — 80-89: Good
- **C** — 70-79: Needs attention
- **D** — 60-69: Needs significant work
- **F** — Below 60: Critical

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

## Authentication

### Personal Access Token (PAT)

The fastest way to get started. Requires a GitHub PAT with `repo` scope.

```bash
export GITHUB_TOKEN=ghp_your_token_here
repo-health-score owner/repo
```

Create a token at: https://github.com/settings/tokens

### GitHub App (coming soon)

For organisations needing fine-grained repo access control and webhook-based real-time updates.

---

## All options

```
usage: repo-health-score [-h] [--token TOKEN] [--all-repos]
                         [--user USER] [--output {json,table,summary}]
                         [--json-output PATH] [--weights JSON]
                         [--exclude REPO [REPO ...]]
                         [repo]

Score the health of GitHub repositories.

positional arguments:
  repo                  Repository in format 'owner/repo'

optional arguments:
  --token, -t           GitHub PAT (or set GITHUB_TOKEN env var)
  --all-repos           Scan all repositories for the authenticated user
  --user, -u            Scan all repos for a specific user/org
  --output              Output format: json, table, or summary (default)
  --json-output         Write JSON output to a file
  --weights             Custom dimension weights as JSON
  --exclude             Repos to exclude from --all-repos or --user scans
```

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. The project follows [Conventional Commits](https://www.conventionalcommits.org/).

---

## License

MIT — see [LICENSE](LICENSE).