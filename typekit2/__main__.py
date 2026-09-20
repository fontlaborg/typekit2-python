# this_file: typekit2/__main__.py
"""Fire-powered command-line interface for typekit2."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

import fire
from dotenv import load_dotenv

from .client import Typekit


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

    @property
    def client(self) -> Typekit:
        """Create the API client lazily so help and doctor work without credentials."""
        return Typekit()

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
        return self.client.list_kits()

    def kit(self, kit_id: str, published: bool = False) -> dict[str, Any]:
        """Get a draft kit or its published version."""
        return self.client.get_kit(kit_id, published=published)

    def family(self, family: str) -> dict[str, Any]:
        """Get a font family by ID or slug."""
        return self.client.get_font_family(family)

    def variations(self, family: str) -> list[str]:
        """List FVD variation codes for a font family."""
        return self.client.get_font_variations(family)

    def libraries(self) -> list[dict[str, Any]]:
        """List font libraries."""
        return self.client.list_libraries()

    def library(self, library: str, page: int = 1, per_page: int = 100) -> dict[str, Any]:
        """Get one paginated font library."""
        return self.client.get_library(library, page=page, per_page=per_page)

    def create_kit(
        self,
        name: str,
        domains: str,
        families: str | None = None,
        segmented_css_names: bool | None = None,
    ) -> dict[str, Any]:
        """Create a draft kit; domains are CSV and families are a JSON list."""
        return self.client.create_kit(
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
        return self.client.update_kit(
            kit_id,
            name=name,
            domains=parse_csv(domains) if domains is not None else None,
            families=parse_families(families),
            segmented_css_names=segmented_css_names,
        )

    def remove_kit(self, kit_id: str) -> dict[str, Any]:
        """Delete a kit. This is a live destructive action."""
        return self.client.remove_kit(kit_id)

    def publish_kit(self, kit_id: str) -> dict[str, Any]:
        """Publish the current draft kit to the CDN."""
        return self.client.publish_kit(kit_id)

    def add_font(
        self,
        kit_id: str,
        family: str,
        variations: str | None = None,
        subset: str = "default",
    ) -> dict[str, Any]:
        """Add or replace one font family in a draft kit."""
        parsed = parse_csv(variations) if variations is not None else None
        return self.client.add_font(kit_id, family, parsed, subset)

    def remove_font(self, kit_id: str, family: str) -> dict[str, Any]:
        """Remove one font family from a draft kit."""
        return self.client.remove_font(kit_id, family)


def _serialize(value: Any) -> str:
    """Produce stable JSON for command results."""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    """Run the typekit2 CLI."""
    fire.Fire(TypekitCLI, name="typekit2", serialize=_serialize)


if __name__ == "__main__":
    main()
