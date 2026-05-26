# Repo Health Score

A unified health scoring tool for GitHub repositories. Track dependency freshness, CI health, PR/issue age, and more — all in one letter grade.

## Installation

```bash
pip install repo-health-score
```

Or install from source:

```bash
git clone https://github.com/CatfishGG/repo-health-score.git
cd repo-health-score
pip install -e .
```

## Quick Start

```bash
# Set your GitHub token
export GITHUB_TOKEN=ghp_your_token_here

# Scan a single repo
repo-health-score owner/repo

# Scan all your repos
repo-health-score --all-repos

# Scan a specific user/org
repo-health-score --user some-org

# Output as JSON
repo-health-score owner/repo --output json
```

## Score Dimensions

| Dimension | Weight | What it measures |
|---|---|---|
| Dependencies | 25% | Security vulnerabilities, outdated packages |
| CI/CD | 20% | Build success rate, workflow health |
| Pull Requests | 20% | PR age, stale PRs, review turnaround |
| Issues | 15% | Issue age, stale issues, response rate |
| Community | 10% | License, contributing guidelines, templates |
| Documentation | 10% | README quality, doc freshness |

## Configuration

### Custom Weights

```bash
repo-health-score owner/repo --weights '{"dependencies":0.4,"ci_cd":0.1}'
```

### Output Formats

```bash
repo-health-score owner/repo --output summary  # Default: human-readable
repo-health-score owner/repo --output table     # Table view
repo-health-score owner/repo --output json      # Full JSON
```

### Write to file

```bash
repo-health-score --all-repos --json-output health-report.json
```

## Authentication

### Personal Access Token (PAT)

```bash
export GITHUB_TOKEN=ghp_your_token
repo-health-score owner/repo
```

PAT requires `repo` scope for full access.

### GitHub App (coming soon)

GitHub App authentication for organisations with tighter permissions.

## License

MIT