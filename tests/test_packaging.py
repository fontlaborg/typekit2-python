# this_file: tests/test_packaging.py

from __future__ import annotations

import subprocess
from pathlib import Path

import tomllib

ROOT = Path(__file__).parents[1]


def test_pyproject_uses_typekit2_hatch_vcs_and_fire_entry_point() -> None:
    with (ROOT / "pyproject.toml").open("rb") as file:
        config = tomllib.load(file)

    assert config["project"]["name"] == "typekit2"
    assert config["project"]["dynamic"] == ["version"]
    assert config["project"]["scripts"] == {"typekit2": "typekit2.__main__:main"}
    assert config["tool"]["hatch"]["version"]["source"] == "vcs"
    assert (
        config["tool"]["hatch"]["build"]["hooks"]["vcs"]["version-file"]
        == "typekit2/__version__.py"
    )


def test_generated_version_file_is_gitignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "typekit2/__version__.py"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_publish_script_has_required_release_commands_and_valid_shell() -> None:
    script = ROOT / "publish.sh"
    text = script.read_text()

    assert script.stat().st_mode & 0o111, "publish.sh must be executable"
    assert "uvx gitnextver" in text
    assert "uv publish" in text
    assert "PUBLISH_SKIP_UPLOAD" in text
    assert "typekit2/__version__.py" in text
    subprocess.run(["bash", "-n", script], check=True)
