# Contributing to Repo Health Score

Thank you for your interest in contributing!

## How to contribute

1. **Fork the repo** and clone it locally
2. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```
4. **Make your changes** and write tests if applicable
5. **Run tests** to make sure everything passes:
   ```bash
   pytest tests/ -v
   ```
6. **Commit your changes** using [Conventional Commits](https://www.conventionalcommits.org/)
7. **Push to your fork** and open a Pull Request

## Conventional Commits

This project follows the Conventional Commits specification. Format your commit messages as:

```
type(scope): description

[optional body]
```

**Types:**
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation changes
- `test` — adding or updating tests
- `refactor` — code refactoring
- `chore` — build process or auxiliary tool changes

**Example:**
```
feat(cli): add --json-output option for machine-readable reports
```

## Reporting bugs

Open an issue and include:
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Python version and platform

## Suggesting features

Open an issue with the `enhancement` label and describe:
- The problem you're trying to solve
- How you envision the solution
- Any alternatives you've considered