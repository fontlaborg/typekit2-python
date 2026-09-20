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
- Updated the Git remote and package metadata for `fontlaborg/typekit2-python`.
- Added compact family discovery, batch-removal preview, verified batch removal, read-only raw GET, and publish-timeout reconciliation to the Fire CLI.

### Verification

- `ruff format --check` and `ruff check`: passed.
- Offline suite: 44 tests passed with 93.93% branch-aware coverage after the CLI workflow extension.
- Fresh `uv build --no-sources`: wheel and sdist built successfully; metadata names `typekit2`, the wheel contains `typekit2/__main__.py` and generated `typekit2/__version__.py`, and no legacy `typekit/` package is present.
- Installed-artifact smoke test from `/tmp`: both `typekit2 doctor` and `python -m typekit2 doctor` returned redacted JSON.
- Disposable release rehearsal: `publish.sh` advanced a local test repository from `v0.1.0` to `v0.1.1`, pushed matching branch/tag refs to a local bare remote, built matching artifacts, and skipped only PyPI upload under `PUBLISH_SKIP_UPLOAD=1`.
- Live read-only CLI checks listed the three Halyard variable families in `gav0zux` and produced a correct three-family removal preview without changing the kit.
