#!/usr/bin/env bash
# this_file: publish.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

die() { printf '%s\n' "$*" >&2; exit 1; }
command -v uv >/dev/null || die 'uv is required.'
command -v uvx >/dev/null || die 'uvx is required.'
[[ "$(git rev-parse --show-prefix)" == "" ]] || die 'Run from the package Git root.'
git symbolic-ref --quiet HEAD >/dev/null || die 'Release from a branch, not detached HEAD.'

version_file=typekit2/__version__.py
git check-ignore --no-index -q "$version_file" || die "$version_file must be gitignored."

# Keep source changes for gitnextver to commit; remove only generated version dirt.
git rm --cached --ignore-unmatch -- "$version_file"
git clean -fX -- "$version_file" .DS_Store
uv sync --frozen --all-groups --reinstall-package typekit2
UV_FROZEN=1 ./test.sh
git clean -fX -- "$version_file" .DS_Store

# gitnextver stages source changes, creates the next SemVer commit/tag, and pushes.
uvx gitnextver --directory "$PWD"
[[ -z "$(git status --porcelain --untracked-files=all)" ]] || die 'gitnextver left uncommitted changes.'
release_tag=$(git describe --exact-match --tags --match 'v[0-9]*' HEAD) ||
    die 'gitnextver did not create a release tag.'
[[ "$release_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "Not a SemVer release tag: $release_tag"

# Revalidate because gitnextver may integrate upstream changes before tagging.
uv sync --frozen --all-groups --reinstall-package typekit2
UV_FROZEN=1 ./test.sh
[[ -z "$(git status --porcelain --untracked-files=all)" ]] || die 'Validation dirtied the release tree.'

# Prove branch and tag reached the remote instead of trusting a success banner.
remote=$(git remote | head -n 1)
if git remote get-url origin >/dev/null 2>&1; then remote=origin; fi
if [[ -n "$remote" ]]; then
    branch=$(git symbolic-ref --short HEAD)
    git push "$remote" "HEAD:refs/heads/$branch" "refs/tags/$release_tag"
    remote_head=$(git ls-remote "$remote" "refs/heads/$branch" | cut -f1)
    remote_tag=$(git ls-remote "$remote" "refs/tags/$release_tag" | cut -f1)
    [[ "$remote_head" == "$(git rev-parse HEAD)" ]] || die 'Remote branch does not match HEAD.'
    [[ "$remote_tag" == "$(git rev-parse "refs/tags/$release_tag")" ]] || die 'Remote tag mismatch.'
fi

# A fresh directory prevents stale dist artifacts from being uploaded.
release_dist=$(mktemp -d "${TMPDIR:-/tmp}/typekit2-release.XXXXXX")
trap 'rm -rf -- "$release_dist"' EXIT
uv build --no-sources --out-dir "$release_dist"
uv run --frozen python - "$release_tag" "$release_dist" <<'PY'
import email
from pathlib import Path
import sys
import tarfile
import zipfile

expected, folder = sys.argv[1].removeprefix("v"), Path(sys.argv[2])
wheels, sdists = list(folder.glob("*.whl")), list(folder.glob("*.tar.gz"))
assert len(wheels) == len(sdists) == 1, "Expected one wheel and one sdist"
with zipfile.ZipFile(wheels[0]) as wheel:
    metadata_name = next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
    assert email.message_from_bytes(wheel.read(metadata_name))["Version"] == expected
    generated = {}
    exec(wheel.read("typekit2/__version__.py"), generated)
    assert generated["__version__"] == expected
with tarfile.open(sdists[0]) as sdist:
    metadata_name = next(member for member in sdist.getmembers() if member.name.endswith("/PKG-INFO"))
    assert email.message_from_bytes(sdist.extractfile(metadata_name).read())["Version"] == expected
print(f"Verified wheel, sdist, and generated version: {expected}")
PY
[[ -z "$(git status --porcelain --untracked-files=all)" ]] || die 'Build dirtied the release tree.'
mkdir -p dist
cp "$release_dist"/*.whl "$release_dist"/*.tar.gz dist/
if [[ "${PUBLISH_SKIP_UPLOAD:-0}" == 1 ]]; then
    printf 'Validated %s; PUBLISH_SKIP_UPLOAD=1 skips only the package upload.\n' "$release_tag"
else
    uv publish "$release_dist"/*.whl "$release_dist"/*.tar.gz "$@"
    printf 'Published %s.\n' "$release_tag"
fi

