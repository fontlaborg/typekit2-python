# this_file: tests/test_cli.py

from __future__ import annotations

import json

import pytest

import typekit2.__main__ as cli_module
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
    monkeypatch.setattr(TypekitCLI, "_client", property(lambda _: fake))
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


def test_cli_uses_configured_timeout_and_exposes_batch_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeClient()
    monkeypatch.setattr("typekit2.__main__.Typekit", lambda timeout: (fake, timeout))
    cli = TypekitCLI(timeout=75)

    assert cli._client == (fake, 75)


def test_cli_batch_commands_parse_and_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(TypekitCLI, "_client", property(lambda _: fake))
    monkeypatch.setattr(
        cli_module,
        "kit_fonts",
        lambda client, kit_id, **kwargs: {"client": client, "kit_id": kit_id, **kwargs},
    )
    monkeypatch.setattr(
        cli_module,
        "plan_remove_fonts",
        lambda client, kit_id, families: {"families": families},
    )
    monkeypatch.setattr(
        cli_module,
        "remove_fonts",
        lambda client, kit_id, families, **kwargs: {"families": families, **kwargs},
    )
    cli = TypekitCLI()

    assert cli.kit_fonts("abc", matching="halyard")["matching"] == "halyard"
    assert cli.plan_remove_fonts("abc", "one,two")["families"] == ["one", "two"]
    result = cli.remove_fonts("abc", "one,two", publish=True, publish_timeout=90)
    assert result["families"] == ["one", "two"]
    assert result["publish"] is True
    assert result["publish_timeout"] == 90


def test_cli_read_only_escape_hatch_parses_json_params(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(TypekitCLI, "_client", property(lambda _: fake))
    cli = TypekitCLI()

    result = cli.request_get("libraries/full", '{"page": 2}')

    assert result["method"] == "request"
    assert result["args"] == ("GET", "libraries/full")
    assert result["kwargs"] == {"params": {"page": 2}}
    with pytest.raises(ValueError, match="JSON object"):
        cli.request_get("libraries/full", "[]")


def test_main_exposes_command_instance_without_public_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}
    monkeypatch.setattr(
        cli_module.fire,
        "Fire",
        lambda component, **kwargs: captured.update(component=component, kwargs=kwargs),
    )

    cli_module.main()

    assert isinstance(captured["component"], TypekitCLI)
    assert not hasattr(captured["component"], "client")
    assert captured["kwargs"]["name"] == "typekit2"
