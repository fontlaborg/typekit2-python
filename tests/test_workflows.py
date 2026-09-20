# this_file: tests/test_workflows.py

from __future__ import annotations

from copy import deepcopy

import pytest

from typekit2.exceptions import TypekitAPIError
from typekit2.workflows import kit_fonts, plan_remove_fonts, remove_fonts


def family(family_id: str, slug: str, name: str | None = None) -> dict:
    return {
        "id": family_id,
        "slug": slug,
        "name": name or slug.replace("-", " ").title(),
        "subset": "default",
        "variations": ["n4"],
    }


class FakeWorkflowClient:
    def __init__(self, families: list[dict]) -> None:
        self.families = deepcopy(families)
        self.published = deepcopy(families)
        self.remove_calls: list[tuple[str, str]] = []
        self.publish_calls: list[tuple[str, float | None]] = []
        self.remove_timeout_ids: set[str] = set()
        self.publish_timeout = False
        self.add_unexpected_family = False

    def get_kit(self, kit_id: str, *, published: bool = False) -> dict:
        selected = self.published if published else self.families
        return {"kit": {"id": kit_id, "families": deepcopy(selected)}}

    def get_published_kit(self, kit_id: str) -> dict:
        return self.get_kit(kit_id, published=True)

    def remove_font(self, kit_id: str, family_id: str) -> dict:
        self.remove_calls.append((kit_id, family_id))
        self.families = [item for item in self.families if item["id"] != family_id]
        if self.add_unexpected_family:
            self.families.append(family("unexpected", "unexpected-font"))
            self.add_unexpected_family = False
        if family_id in self.remove_timeout_ids:
            raise TypekitAPIError("request timed out")
        return {"ok": True}

    def publish_kit(self, kit_id: str, *, timeout: float | None = None) -> dict:
        self.publish_calls.append((kit_id, timeout))
        self.published = deepcopy(self.families)
        if self.publish_timeout:
            raise TypekitAPIError("request timed out")
        return {"published": "now"}

    def request(self, method: str, path: str, **kwargs) -> dict:
        return {"method": method, "path": path, **kwargs}


HALYARD = [
    family("ykgy", "halyard-display"),
    family("hfhh", "halyard-micro"),
    family("gvck", "halyard-text"),
    family("bqky", "halyard-display-variable"),
    family("nqbl", "halyard-micro-variable"),
    family("cnlf", "halyard-text-variable"),
    family("other", "other-font"),
]


def test_kit_fonts_returns_compact_sorted_filtered_records() -> None:
    client = FakeWorkflowClient(HALYARD)

    result = kit_fonts(client, "kit123", matching="variable")

    assert result["kit_id"] == "kit123"
    assert result["family_count"] == 3
    assert [item["slug"] for item in result["families"]] == [
        "halyard-display-variable",
        "halyard-micro-variable",
        "halyard-text-variable",
    ]


def test_plan_remove_fonts_resolves_slugs_ids_and_names_without_writing() -> None:
    client = FakeWorkflowClient(HALYARD)

    result = plan_remove_fonts(client, "kit123", ["halyard-display", "hfhh", "Halyard Text"])

    assert result["status"] == "preview"
    assert [item["id"] for item in result["remove"]] == ["ykgy", "hfhh", "gvck"]
    assert result["before_family_count"] == 7
    assert result["after_family_count"] == 4
    assert client.remove_calls == []


def test_remove_fonts_rejects_missing_identifier_before_writing() -> None:
    client = FakeWorkflowClient(HALYARD)

    with pytest.raises(ValueError, match="not present"):
        remove_fonts(client, "kit123", ["halyard-display", "typo"])

    assert client.remove_calls == []


def test_remove_fonts_preserves_every_unrequested_family_and_publishes() -> None:
    client = FakeWorkflowClient(HALYARD)

    result = remove_fonts(
        client,
        "kit123",
        ["halyard-display", "halyard-micro", "halyard-text"],
        publish=True,
        publish_timeout=120,
    )

    assert result["status"] == "removed"
    assert result["before_family_count"] == 7
    assert result["after_family_count"] == 4
    assert result["unrelated_families_preserved"] is True
    assert result["publish"] == {"status": "accepted", "response": {"published": "now"}}
    assert client.publish_calls == [("kit123", 120)]
    assert {item["slug"] for item in client.families} == {
        "halyard-display-variable",
        "halyard-micro-variable",
        "halyard-text-variable",
        "other-font",
    }


def test_remove_fonts_reconciles_delete_and_publish_timeouts() -> None:
    client = FakeWorkflowClient(HALYARD)
    client.remove_timeout_ids = {"ykgy"}
    client.publish_timeout = True

    result = remove_fonts(client, "kit123", ["ykgy"], publish=True)

    assert result["removed"][0]["id"] == "ykgy"
    assert result["publish"]["status"] == "confirmed-after-error"
    assert "timed out" in result["publish"]["error"]


def test_remove_fonts_can_preview_or_ignore_already_absent_families() -> None:
    client = FakeWorkflowClient(HALYARD)

    preview = remove_fonts(client, "kit123", ["halyard-display"], dry_run=True)
    absent = remove_fonts(client, "kit123", ["missing"], ignore_missing=True)

    assert preview["status"] == "preview"
    assert absent["status"] == "no-changes"
    assert absent["missing"] == ["missing"]
    assert client.remove_calls == []


def test_remove_fonts_fails_if_any_unrequested_family_changes() -> None:
    client = FakeWorkflowClient(HALYARD)
    client.add_unexpected_family = True

    with pytest.raises(TypekitAPIError, match="unexpected kit changes") as error:
        remove_fonts(client, "kit123", ["halyard-display"])

    assert error.value.errors[0]["unexpectedly_added"] == ["unexpected"]
