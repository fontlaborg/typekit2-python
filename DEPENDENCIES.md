---
this_file: DEPENDENCIES.md
---

# Dependencies

## Runtime

- `requests`: HTTP transport with sessions, TLS verification, timeouts, and explicit status handling.
- `python-dotenv`: loads `TYPEKIT_API_KEY` from `.env` while preserving environment precedence.
- `fire`: generates the requested CLI from the small `TypekitCLI` command object.

## Build and release

- `hatchling`: PEP 517 build backend configured in `pyproject.toml`.
- `hatch-vcs`: derives PEP 440 versions from semantic Git tags and writes the packaged `__version__.py`.
- `gitnextver` (run with `uvx`): creates the next semantic version commit/tag and pushes it during releases.
- `uv`: resolves dependencies, runs checks, builds wheel/sdist, and publishes distributions.

## Development

- `pytest` and `pytest-cov`: offline contract tests and coverage enforcement.
- `ruff`: formatting and static lint checks.

