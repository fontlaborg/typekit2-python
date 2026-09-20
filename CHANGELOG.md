---
this_file: CHANGELOG.md
---

# Changelog

## Unreleased

### Changed

- Updated project links for the renamed `fontlaborg/typekit2-python` repository.
- Renamed the distribution and import package from `typekit` to `typekit2`.
- Replaced `setup.py` with standards-based `pyproject.toml` packaging.
- Migrated the client from Python 2 to typed Python 3.10+.
- Switched authentication from URL query parameters to the documented HTTPS `X-Typekit-Token` header.
- Reworked kit writes to use current parameter shapes and preserve omitted update fields.

### Added

- `TYPEKIT_API_KEY` and `.env` configuration through `python-dotenv`.
- Fire CLI via `python -m typekit2` and the `typekit2` console command.
- Adobe Fonts API mapping and usage documentation.
- Offline tests for authentication, transport, payloads, errors, parsing, and CLI behavior.
- Tag-derived semantic versions using `hatch-vcs`.
- `publish.sh` workflow using `uvx gitnextver`, `uv build`, and `uv publish`.
- Compact `kit-fonts` discovery and read-only `request-get` escape-hatch commands.
- Safe `plan-remove-fonts` and `remove-fonts` batch workflows with ID resolution, dry-run, full preservation checks, optional publish, and timeout reconciliation.
- Official Adobe API Token page in setup and API documentation.

### Removed

- Python 2-only code, live destructive tests, `setup.py`, and generated distutils manifest.
