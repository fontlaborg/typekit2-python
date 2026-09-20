#!/usr/bin/env bash
# this_file: test.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

uv run ruff format --check .
uv run ruff check .
uv run pytest

