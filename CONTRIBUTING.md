# Contributing to Mnemo

Thank you for your interest in contributing!

## Development setup

**Prerequisites:** [uv](https://docs.astral.sh/uv/) ≥ 0.5

```bash
git clone https://github.com/yourorg/mnemo
cd mnemo

# Install all dev dependencies (creates .venv automatically)
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install --install-hooks
```

## Daily workflow

```bash
# Run the full test suite
uv run pytest

# Run only fast unit tests
uv run pytest -m "not slow and not integration"

# Run linting + formatting
uv run ruff check --fix .
uv run ruff format .

# Type check
uv run mypy src/mnemo
uv run pyright src/mnemo

# Build and serve docs locally
uv run mkdocs serve
```

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/).
The pre-commit hook will enforce this on `commit-msg`.

| Type       | When to use                              |
|------------|------------------------------------------|
| `feat`     | New user-facing feature                  |
| `fix`      | Bug fix                                  |
| `docs`     | Documentation only                       |
| `refactor` | Code change without feature/fix          |
| `test`     | Tests added or changed                   |
| `perf`     | Performance improvement                  |
| `ci`       | CI/CD changes                            |
| `chore`    | Maintenance (deps, tooling)              |

Examples:
```
feat(backends): add Redis backend with vector similarity search
fix(store): handle empty content string in InMemoryBackend.search
docs: add custom backend guide to mkdocs
```

## Pull requests

1. Open an issue first for non-trivial changes.
2. Branch off `main`: `git checkout -b feat/my-feature`.
3. Write tests; aim for > 80 % coverage on new code.
4. Run `uv run pytest` and `uv run ruff check .` locally before pushing.
5. Open a PR against `main` — CI will run automatically.

## Release process (maintainers only)

1. Update `CHANGELOG.md` — move "Unreleased" items under the new version.
2. Bump `version` in `pyproject.toml` and `src/mnemo/_version.py`.
3. Commit: `chore(release): bump version to X.Y.Z`.
4. Tag: `git tag vX.Y.Z && git push --tags`.
5. Create a GitHub Release from the tag — the publish workflow fires automatically.
