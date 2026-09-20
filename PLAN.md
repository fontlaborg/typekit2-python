---
this_file: PLAN.md
---

# Plan

The modernization target is a maintained Python 3 package whose library, CLI, documentation, and release artifacts agree with the current Adobe Fonts API contract.

## Completed scope

- Rename both distribution and imports to `typekit2`.
- Replace legacy setup metadata with `pyproject.toml` and `hatch-vcs` versions.
- Modernize the HTTP client, HTTPS authentication, errors, typing, and API payloads.
- Load `TYPEKIT_API_KEY` from the environment or `.env`.
- Add a Fire CLI for reads and explicit kit mutations.
- Replace live account-mutating tests with deterministic request-level tests.
- Document Adobe endpoints, parameter semantics, installation, API, CLI, and releases.
- Add a guarded `gitnextver` and `uv publish` release workflow.
- Add compact kit-family discovery and verified multi-family removal/publish workflows.

## Future work

- Add opt-in live read-only smoke tests when a dedicated Adobe Fonts test account is available.
- Add API resources only when they appear in Adobe’s authoritative reference.
