# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
specification.

## [Unreleased]

### Added
- Initial project scaffold with `src` layout
- `MemoryBackend` Protocol for backend-agnostic plugin interface
- `BaseBackend` ABC for first-party backends with shared lifecycle logic
- `InMemoryBackend` for tests and prototyping
- `MemoryStore` async-first high-level API
- `SyncMemoryStore` thin shim for non-async callers (via AnyIO)
- Full type annotations; `py.typed` marker for PEP 561 compliance
- Ruff, Mypy (strict), Pyright (strict) configuration
- Pytest with coverage, asyncio auto-mode, and custom markers
- GitHub Actions CI: lint, typecheck, test matrix (3.10, 3.11, 3.12)
- GitHub Actions publish workflow with OIDC Trusted Publishing
- Pre-commit hooks: ruff, mypy, conventional-commits
- MkDocs-Material documentation with mkdocstrings

## [0.1.0] — Unreleased

[Unreleased]: https://github.com/yourorg/mnemo/compare/v0.1.0...HEAD
