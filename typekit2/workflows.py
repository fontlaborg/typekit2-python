# this_file: typekit2/workflows.py
"""Safe, composable workflows built on the Adobe Fonts API client."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .exceptions import TypekitAPIError


def _load_families(client: Any, kit_id: str, *, published: bool = False) -> list[dict[str, Any]]:
    payload = client.get_published_kit(kit_id) if published else client.get_kit(kit_id)
    families = payload.get("kit", {}).get("families")
    if not isinstance(families, list) or not all(isinstance(item, dict) for item in families):
        raise TypekitAPIError("Adobe Fonts returned an invalid kit family list")
    return families


def _compact(family: dict[str, Any]) -> dict[str, Any]:
    return {
        key: family[key] for key in ("id", "slug", "name", "subset", "variations") if key in family
    }


def _identifiers(values: str | Sequence[str]) -> list[str]:
    items = values.split(",") if isinstance(values, str) else list(values)
    parsed = [str(item).strip() for item in items if str(item).strip()]
    if not parsed:
        raise ValueError("families must contain at least one ID, slug, or name")
    return parsed


def _resolve(
    families: list[dict[str, Any]], identifiers: list[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    lookup: dict[str, dict[str, dict[str, Any]]] = {}
    for family in families:
        for field in ("id", "slug", "name"):
            value = family.get(field)
            if isinstance(value, str):
                lookup.setdefault(value.casefold(), {})[str(family.get("id"))] = family
    resolved: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[str] = set()
    for identifier in identifiers:
        matches = list(lookup.get(identifier.casefold(), {}).values())
        if not matches:
            missing.append(identifier)
            continue
        if len(matches) > 1:
            raise ValueError(f"family identifier is ambiguous: {identifier}")
        family = matches[0]
        family_id = str(family["id"])
        if family_id not in seen:
            resolved.append(family)
            seen.add(family_id)
    return resolved, missing


def _plan(
    kit_id: str, families: list[dict[str, Any]], identifiers: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    resolved, missing = _resolve(families, identifiers)
    plan = {
        "status": "preview",
        "kit_id": kit_id,
        "requested": identifiers,
        "remove": [_compact(family) for family in resolved],
        "missing": missing,
        "before_family_count": len(families),
        "after_family_count": len(families) - len(resolved),
    }
    return plan, resolved


def kit_fonts(
    client: Any,
    kit_id: str,
    *,
    matching: str | None = None,
    published: bool = False,
) -> dict[str, Any]:
    """Return a concise, optionally filtered family inventory for one kit."""
    families = _load_families(client, kit_id, published=published)
    if matching:
        needle = matching.casefold()
        families = [
            family
            for family in families
            if any(
                needle in str(family.get(field, "")).casefold() for field in ("id", "slug", "name")
            )
        ]
    compact = sorted(
        (_compact(family) for family in families), key=lambda item: item.get("slug", "")
    )
    return {
        "kit_id": kit_id,
        "published": published,
        "matching": matching,
        "family_count": len(compact),
        "families": compact,
    }


def plan_remove_fonts(client: Any, kit_id: str, families: str | Sequence[str]) -> dict[str, Any]:
    """Resolve a batch removal by ID, slug, or name without changing the kit."""
    current = _load_families(client, kit_id)
    plan, _ = _plan(kit_id, current, _identifiers(families))
    return plan


def _verify_removal(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    removed: list[dict[str, Any]],
) -> None:
    before_ids = {str(family["id"]) for family in before}
    removed_ids = {str(family["id"]) for family in removed}
    after_ids = {str(family["id"]) for family in after}
    expected_ids = before_ids - removed_ids
    if after_ids != expected_ids:
        raise TypekitAPIError(
            "Post-removal verification found unexpected kit changes",
            errors=[
                {
                    "still_present": sorted(removed_ids & after_ids),
                    "unexpectedly_removed": sorted(expected_ids - after_ids),
                    "unexpectedly_added": sorted(after_ids - expected_ids),
                }
            ],
        )


def _publish_verified(
    client: Any, kit_id: str, after: list[dict[str, Any]], timeout: float
) -> dict[str, Any]:
    try:
        response = client.publish_kit(kit_id, timeout=timeout)
    except TypekitAPIError as error:
        published = _load_families(client, kit_id, published=True)
        expected_ids = {str(family["id"]) for family in after}
        published_ids = {str(family["id"]) for family in published}
        if published_ids == expected_ids:
            return {"status": "confirmed-after-error", "error": str(error)}
        raise TypekitAPIError(
            "Publish outcome is indeterminate; the published kit does not match the verified draft",
            errors=[{"original_error": str(error)}],
        ) from error
    return {"status": "accepted", "response": response}


def remove_fonts(
    client: Any,
    kit_id: str,
    families: str | Sequence[str],
    *,
    publish: bool = False,
    dry_run: bool = False,
    ignore_missing: bool = False,
    publish_timeout: float = 120.0,
) -> dict[str, Any]:
    """Remove several families while proving all unrequested families remain."""
    before = _load_families(client, kit_id)
    plan, resolved = _plan(kit_id, before, _identifiers(families))
    if plan["missing"] and not ignore_missing:
        missing = ", ".join(plan["missing"])
        raise ValueError(f"families are not present in kit {kit_id}: {missing}")
    if dry_run:
        return plan
    if not resolved:
        return {**plan, "status": "no-changes", "publish": {"status": "skipped"}}
    for family in resolved:
        try:
            client.remove_font(kit_id, str(family["id"]))
        except TypekitAPIError:
            current_ids = {str(item["id"]) for item in _load_families(client, kit_id)}
            if str(family["id"]) in current_ids:
                raise
    after = _load_families(client, kit_id)
    _verify_removal(before, after, resolved)
    result = {
        **plan,
        "status": "removed",
        "removed": [_compact(family) for family in resolved],
        "after_family_count": len(after),
        "unrelated_families_preserved": True,
        "publish": {"status": "skipped"},
    }
    if publish:
        result["publish"] = _publish_verified(client, kit_id, after, publish_timeout)
    return result
