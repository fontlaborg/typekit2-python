# this_file: tests/test_cli.py

from __future__ import annotations

import json

import pytest

from typekit2.__main__ import TypekitCLI, _serialize, parse_csv, parse_families


def test_parse_csv_accepts_string_and_sequence() -> None:
    assert parse_csv("example.com, www.example.com") == ["example.com", "www.example.com"]
    assert parse_csv(["example.com", "www.example.com"]) == ["example.com", "www.example.com"]


def test_parse_families_accepts_json() -> None:
    value = json.dumps([{"id": "pcpv", "variations": ["n4", "i4"]}])

    assert parse_families(value) == [{"id": "pcpv", "variations": ["n4", "i4"]}]


def test_parse_families_rejects_non_list_json() -> None:
    with pytest.raises(ValueError, match="JSON list"):
        parse_families('{"id": "pcpv"}')


def test_doctor_never_discloses_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TYPEKIT_API_KEY", "do-not-print-me")

    result = TypekitCLI().doctor()

    assert result == {"api_key": "configured", "source": "environment-or-dotenv"}
    assert "do-not-print-me" not in repr(result)


def test_doctor_reports_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TYPEKIT_API_KEY", raising=False)
    monkeypatch.setattr("typekit2.__main__.load_dotenv", lambda: False)

    assert TypekitCLI().doctor() == {"api_key": "missing", "source": "none"}


def test_parsers_reject_empty_csv_and_preserve_existing_family_list() -> None:
    families = [{"id": "pcpv"}]

    with pytest.raises(ValueError, match="at least one"):
        parse_csv(" , ")

    assert parse_families(None) is None
    assert parse_families(families) is families


def test_serializer_returns_stable_json() -> None:
    assert _serialize({"b": 1, "a": "ą"}) == '{\n  "a": "ą",\n  "b": 1\n}'


class FakeClient:
    def __getattr__(self, name: str):
        def method(*args, **kwargs):
            return {"method": name, "args": args, "kwargs": kwargs}

        return method


def test_cli_commands_delegate_with_parsed_values(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(TypekitCLI, "client", property(lambda _: fake))
    cli = TypekitCLI()

    assert cli.kits()["method"] == "list_kits"
    assert cli.kit("abc", True)["kwargs"] == {"published": True}
    assert cli.family("pcpv")["method"] == "get_font_family"
    assert cli.variations("pcpv")["method"] == "get_font_variations"
    assert cli.libraries()["method"] == "list_libraries"
    assert cli.library("full", 2, 50)["kwargs"] == {"page": 2, "per_page": 50}
    assert cli.create_kit("Example", "a.test,b.test")["args"][1] == ["a.test", "b.test"]
    assert cli.update_kit("abc", domains="a.test,b.test")["kwargs"]["domains"] == [
        "a.test",
        "b.test",
    ]
    assert cli.remove_kit("abc")["method"] == "remove_kit"
    assert cli.publish_kit("abc")["method"] == "publish_kit"
    assert cli.add_font("abc", "pcpv", "n4,i4")["args"][2] == ["n4", "i4"]
    assert cli.remove_font("abc", "pcpv")["method"] == "remove_font"
