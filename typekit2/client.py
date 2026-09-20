# this_file: typekit2/client.py
"""Adobe Fonts (Typekit) API client."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from .__version__ import __version__
from .exceptions import TypekitAPIError, TypekitConfigurationError

DEFAULT_BASE_URL = "https://typekit.com/api/v1/json"
DEFAULT_TIMEOUT = 30.0

FormData = list[tuple[str, str]]
Family = Mapping[str, Any]


def _as_list(value: str | Sequence[str], field: str) -> list[str]:
    """Parse a non-empty string or sequence at the public API boundary."""
    values = [value] if isinstance(value, str) else list(value)
    if not values or not all(isinstance(item, str) and item.strip() for item in values):
        raise ValueError(f"{field} must contain at least one non-empty string")
    return [item.strip() for item in values]


def _kit_form(
    *,
    name: str | None = None,
    domains: str | Sequence[str] | None = None,
    families: Sequence[Family] | None = None,
    segmented_css_names: bool | None = None,
) -> FormData:
    """Encode documented Rails-style kit form parameters."""
    data: FormData = []
    if name is not None:
        if not name.strip():
            raise ValueError("name must not be empty")
        data.append(("name", name))
    if domains is not None:
        data.extend(("domains[]", domain) for domain in _as_list(domains, "domains"))
    if families is not None:
        for index, family in enumerate(families):
            family_id = family.get("id")
            if not isinstance(family_id, str) or not family_id.strip():
                raise ValueError(f"families[{index}].id must be a non-empty string")
            prefix = f"families[{index}]"
            data.append((f"{prefix}[id]", family_id.strip()))
            subset = family.get("subset")
            if subset is not None:
                if subset not in {"default", "all"}:
                    raise ValueError(f"families[{index}].subset must be 'default' or 'all'")
                data.append((f"{prefix}[subset]", subset))
            variations = family.get("variations")
            if variations is not None:
                data.append((f"{prefix}[variations]", ",".join(_as_list(variations, "variations"))))
    if segmented_css_names is not None:
        data.append(("segmented_css_names", str(segmented_css_names).lower()))
    return data


class Typekit:
    """Client for the Adobe Fonts API documented at fonts.adobe.com/docs/api."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        api_token: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        session: requests.Session | Any | None = None,
    ) -> None:
        load_dotenv()
        key = api_key or api_token or os.getenv("TYPEKIT_API_KEY")
        if not key or not key.strip():
            raise TypekitConfigurationError(
                "Set TYPEKIT_API_KEY in the environment or .env, or pass api_key explicitly"
            )
        if not base_url.startswith("https://"):
            raise TypekitConfigurationError("Authenticated API requests require an HTTPS base URL")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self.api_key = key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def request(
        self,
        method: str,
        path: str,
        *,
        data: FormData | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request and return the decoded JSON object."""
        kwargs: dict[str, Any] = {
            "headers": {
                "User-Agent": f"typekit2/{__version__}",
                "X-Typekit-Token": self.api_key,
            },
            "timeout": self.timeout,
        }
        if data is not None:
            kwargs["data"] = data
        if params is not None:
            kwargs["params"] = dict(params)
        try:
            response = self.session.request(
                method.upper(), f"{self.base_url}/{path.lstrip('/')}", **kwargs
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            raise TypekitAPIError(
                f"Adobe Fonts request failed: {error}", status_code=status
            ) from error
        except ValueError as error:
            raise TypekitAPIError("Adobe Fonts returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise TypekitAPIError("Adobe Fonts returned a non-object JSON response")
        errors = payload.get("errors")
        if errors:
            normalized = errors if isinstance(errors, list) else [errors]
            raise TypekitAPIError("Adobe Fonts API returned errors", errors=normalized)
        return payload

    def list_kits(self) -> list[dict[str, Any]]:
        """Return kits owned by the authenticated user."""
        return self.request("GET", "kits").get("kits", [])

    def get_kit(self, kit_id: str, *, published: bool = False) -> dict[str, Any]:
        """Return a draft kit, or its published version when requested."""
        suffix = "/published" if published else ""
        return self.request("GET", f"kits/{quote(kit_id, safe='')}{suffix}")

    def get_published_kit(self, kit_id: str) -> dict[str, Any]:
        """Return the version of a kit currently published to the CDN."""
        return self.get_kit(kit_id, published=True)

    def create_kit(
        self,
        name: str,
        domains: str | Sequence[str],
        families: Sequence[Family] | None = None,
        segmented_css_names: bool | None = None,
    ) -> dict[str, Any]:
        """Create a draft kit."""
        data = _kit_form(
            name=name,
            domains=domains,
            families=families,
            segmented_css_names=segmented_css_names,
        )
        return self.request("POST", "kits", data=data)

    def update_kit(
        self,
        kit_id: str,
        name: str | None = None,
        domains: str | Sequence[str] | None = None,
        families: Sequence[Family] | None = None,
        segmented_css_names: bool | None = None,
    ) -> dict[str, Any]:
        """Replace only the supplied draft-kit attributes."""
        data = _kit_form(
            name=name,
            domains=domains,
            families=families,
            segmented_css_names=segmented_css_names,
        )
        if not data:
            raise ValueError("update_kit requires at least one field")
        return self.request("POST", f"kits/{quote(kit_id, safe='')}", data=data)

    def remove_kit(self, kit_id: str) -> dict[str, Any]:
        """Delete a kit."""
        return self.request("DELETE", f"kits/{quote(kit_id, safe='')}")

    def publish_kit(self, kit_id: str) -> dict[str, Any]:
        """Publish the current draft kit asynchronously."""
        return self.request("POST", f"kits/{quote(kit_id, safe='')}/publish")

    def get_font_family(self, family: str) -> dict[str, Any]:
        """Return a font family by ID or slug."""
        return self.request("GET", f"families/{quote(family, safe='')}")

    def get_font_variations(self, family: str) -> list[str]:
        """Return Font Variation Description values for a family."""
        variations = self.get_font_family(family).get("family", {}).get("variations", [])
        return [item["fvd"] for item in variations if isinstance(item, dict) and "fvd" in item]

    def list_libraries(self) -> list[dict[str, Any]]:
        """Return available Adobe Fonts libraries."""
        return self.request("GET", "libraries").get("libraries", [])

    def get_library(self, library: str, *, page: int = 1, per_page: int = 100) -> dict[str, Any]:
        """Return a paginated font library."""
        if page < 1 or per_page < 1:
            raise ValueError("page and per_page must be positive integers")
        return self.request(
            "GET",
            f"libraries/{quote(library, safe='')}",
            params={"page": page, "per_page": per_page},
        )

    def add_font(
        self,
        kit_id: str,
        family: str,
        variations: str | Sequence[str] | None = None,
        subset: str = "default",
    ) -> dict[str, Any]:
        """Add or replace one font family in a draft kit."""
        if subset not in {"default", "all"}:
            raise ValueError("subset must be 'default' or 'all'")
        data: FormData = [("subset", subset)]
        if variations is not None:
            data.append(("variations", ",".join(_as_list(variations, "variations"))))
        path = f"kits/{quote(kit_id, safe='')}/families/{quote(family, safe='')}"
        return self.request("POST", path, data=data)

    def remove_font(self, kit_id: str, family: str) -> dict[str, Any]:
        """Remove one font family from a draft kit."""
        path = f"kits/{quote(kit_id, safe='')}/families/{quote(family, safe='')}"
        return self.request("DELETE", path)

    def kit_contains_font(self, kit_id: str, family: str) -> bool:
        """Return whether the draft kit contains the resolved family ID."""
        family_id = self.get_font_family(family).get("family", {}).get("id")
        return family_id in self.get_kit_fonts(kit_id)

    def get_kit_fonts(self, kit_id: str) -> list[str]:
        """Return family IDs in a draft kit."""
        families = self.get_kit(kit_id).get("kit", {}).get("families", [])
        return [item["id"] for item in families if isinstance(item, dict) and "id" in item]

    kit_add_font = add_font
    kit_remove_font = remove_font
