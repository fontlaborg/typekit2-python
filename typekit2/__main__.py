# this_file: typekit2/__main__.py
"""Fire-powered command-line interface for typekit2."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

import fire
from dotenv import load_dotenv

from .client import DEFAULT_TIMEOUT, Typekit
from .workflows import kit_fonts, plan_remove_fonts, remove_fonts


def parse_csv(value: str | Sequence[str]) -> list[str]:
    """Parse a comma-separated Fire argument or an existing sequence."""
    items = value.split(",") if isinstance(value, str) else list(value)
    parsed = [str(item).strip() for item in items if str(item).strip()]
    if not parsed:
        raise ValueError("expected at least one value")
    return parsed


def parse_families(value: str | list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    """Parse a JSON list accepted by create-kit and update-kit."""
    if value is None or isinstance(value, list):
        return value
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ValueError("families must be a JSON list of objects")
    return parsed


class TypekitCLI:
    """Read and manage Adobe Fonts kits and font metadata."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Configure the default HTTP timeout in seconds."""
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self._timeout = timeout

    @property
    def _client(self) -> Typekit:
        """Create the API client lazily so help and doctor work without credentials."""
        return Typekit(timeout=self._timeout)

    def doctor(self) -> dict[str, str]:
        """Check whether TYPEKIT_API_KEY is available without revealing it."""
        load_dotenv()
        configured = bool(os.getenv("TYPEKIT_API_KEY", "").strip())
        return {
            "api_key": "configured" if configured else "missing",
            "source": "environment-or-dotenv" if configured else "none",
        }

    def kits(self) -> list[dict[str, Any]]:
        """List kits owned by the authenticated user."""
        return self._client.list_kits()

    def kit(self, kit_id: str, published: bool = False) -> dict[str, Any]:
        """Get a draft kit or its published version."""
        return self._client.get_kit(kit_id, published=published)

    def family(self, family: str) -> dict[str, Any]:
        """Get a font family by ID or slug."""
        return self._client.get_font_family(family)

    def variations(self, family: str) -> list[str]:
        """List FVD variation codes for a font family."""
        return self._client.get_font_variations(family)

    def libraries(self) -> list[dict[str, Any]]:
        """List font libraries."""
        return self._client.list_libraries()

    def library(self, library: str, page: int = 1, per_page: int = 100) -> dict[str, Any]:
        """Get one paginated font library."""
        return self._client.get_library(library, page=page, per_page=per_page)

    def create_kit(
        self,
        name: str,
        domains: str,
        families: str | None = None,
        segmented_css_names: bool | None = None,
    ) -> dict[str, Any]:
        """Create a draft kit; domains are CSV and families are a JSON list."""
        return self._client.create_kit(
            name,
            parse_csv(domains),
            parse_families(families),
            segmented_css_names,
        )

    def update_kit(
        self,
        kit_id: str,
        name: str | None = None,
        domains: str | None = None,
        families: str | None = None,
        segmented_css_names: bool | None = None,
    ) -> dict[str, Any]:
        """Update supplied draft-kit fields."""
        return self._client.update_kit(
            kit_id,
            name=name,
            domains=parse_csv(domains) if domains is not None else None,
            families=parse_families(families),
            segmented_css_names=segmented_css_names,
        )

    def remove_kit(self, kit_id: str) -> dict[str, Any]:
        """Delete a kit. This is a live destructive action."""
        return self._client.remove_kit(kit_id)

    def publish_kit(self, kit_id: str, timeout: float = 120.0) -> dict[str, Any]:
        """Publish the current draft kit to the CDN."""
        return self._client.publish_kit(kit_id, timeout=timeout)

    def add_font(
        self,
        kit_id: str,
        family: str,
        variations: str | None = None,
        subset: str = "default",
    ) -> dict[str, Any]:
        """Add or replace one font family in a draft kit."""
        parsed = parse_csv(variations) if variations is not None else None
        return self._client.add_font(kit_id, family, parsed, subset)

    def remove_font(self, kit_id: str, family: str) -> dict[str, Any]:
        """Remove one font family from a draft kit."""
        return self._client.remove_font(kit_id, family)

    def kit_fonts(
        self,
        kit_id: str,
        matching: str | None = None,
        published: bool = False,
    ) -> dict[str, Any]:
        """List concise kit families, optionally filtered by ID, slug, or name."""
        return kit_fonts(self._client, kit_id, matching=matching, published=published)

    def plan_remove_fonts(self, kit_id: str, families: str) -> dict[str, Any]:
        """Preview a batch removal using comma-separated IDs, slugs, or names."""
        return plan_remove_fonts(self._client, kit_id, parse_csv(families))

    def remove_fonts(
        self,
        kit_id: str,
        families: str,
        publish: bool = False,
        dry_run: bool = False,
        ignore_missing: bool = False,
        publish_timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Remove several families, preserve all others, and optionally publish."""
        return remove_fonts(
            self._client,
            kit_id,
            parse_csv(families),
            publish=publish,
            dry_run=dry_run,
            ignore_missing=ignore_missing,
            publish_timeout=publish_timeout,
        )

    def request_get(self, path: str, params: str | None = None) -> dict[str, Any]:
        """Make an authenticated raw GET; params is an optional JSON object."""
        parsed = json.loads(params) if params else None
        if parsed is not None and not isinstance(parsed, dict):
            raise ValueError("params must be a JSON object")
        return self._client.request("GET", path, params=parsed)


def _serialize(value: Any) -> str:
    """Produce stable JSON for command results."""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    """Run the typekit2 CLI."""
    fire.Fire(TypekitCLI(), name="typekit2", serialize=_serialize)


if __name__ == "__main__":
    main()
