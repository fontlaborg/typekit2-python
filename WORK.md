---
this_file: WORK.md
---

# Work log

## 2026-09-20

- Audited the Python 2 package, destructive live tests, and setup metadata.
- Checked current Adobe Fonts authentication, request, parameter, kit, family, and library documentation.
- Checked current Python Fire, python-dotenv, hatch-vcs, and uv packaging guidance.
- Renamed the package to `typekit2` and implemented the modern client and CLI.
- Added offline contract tests before implementation.
- Added tag-derived versioning and a guarded publish workflow.

### Verification

- `ruff format --check` and `ruff check`: passed.
- Offline suite: 31 tests passed with 95.67% branch-aware coverage.
- Fresh `uv build --no-sources`: wheel and sdist built successfully; metadata names `typekit2`, the wheel contains `typekit2/__main__.py` and generated `typekit2/__version__.py`, and no legacy `typekit/` package is present.
- Installed-artifact smoke test from `/tmp`: both `typekit2 doctor` and `python -m typekit2 doctor` returned redacted JSON.
- Disposable release rehearsal: `publish.sh` advanced a local test repository from `v0.1.0` to `v0.1.1`, pushed matching branch/tag refs to a local bare remote, built matching artifacts, and skipped only PyPI upload under `PUBLISH_SKIP_UPLOAD=1`.
