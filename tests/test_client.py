# this_file: tests/test_client.py

from __future__ import annotations

import pytest
import requests

from typekit2 import Typekit, __version__
from typekit2.exceptions import TypekitAPIError, TypekitConfigurationError


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class InvalidJSONResponse(FakeResponse):
    def json(self) -> dict:
        raise ValueError("invalid JSON")


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.response


def test_client_reads_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TYPEKIT_API_KEY", "env-secret")

    client = Typekit()

    assert client.api_key == "env-secret", "TYPEKIT_API_KEY should configure the client"


def test_client_rejects_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TYPEKIT_API_KEY", raising=False)
    monkeypatch.setattr("typekit2.client.load_dotenv", lambda: False)

    with pytest.raises(TypekitConfigurationError, match="TYPEKIT_API_KEY"):
        Typekit()


def test_list_kits_uses_https_header_auth_and_timeout() -> None:
    session = FakeSession(FakeResponse({"kits": [{"id": "abc123"}]}))
    client = Typekit(api_key="secret", session=session, timeout=7.5)

    assert client.list_kits() == [{"id": "abc123"}]
    assert session.calls == [
        {
            "method": "GET",
            "url": "https://typekit.com/api/v1/json/kits",
            "headers": {
                "User-Agent": f"typekit2/{__version__}",
                "X-Typekit-Token": "secret",
            },
            "timeout": 7.5,
        }
    ], "tokens must be sent in the documented header, never in the URL"


def test_create_kit_encodes_nested_families() -> None:
    session = FakeSession(FakeResponse({"kit": {"id": "abc123"}}))
    client = Typekit(api_key="secret", session=session)

    result = client.create_kit(
        "Example",
        ["example.com", "www.example.com"],
        [{"id": "pcpv", "subset": "all", "variations": ["n4", "i4"]}],
    )

    assert result == {"kit": {"id": "abc123"}}
    assert session.calls[0]["data"] == [
        ("name", "Example"),
        ("domains[]", "example.com"),
        ("domains[]", "www.example.com"),
        ("families[0][id]", "pcpv"),
        ("families[0][subset]", "all"),
        ("families[0][variations]", "n4,i4"),
    ]


def test_update_kit_does_not_replace_omitted_fields() -> None:
    session = FakeSession(FakeResponse({"kit": {"id": "abc123", "name": "Renamed"}}))
    client = Typekit(api_key="secret", session=session)

    client.update_kit("abc123", name="Renamed")

    assert session.calls[0]["data"] == [("name", "Renamed")]


def test_get_library_passes_pagination_as_query_parameters() -> None:
    session = FakeSession(FakeResponse({"library": {"id": "full"}}))
    client = Typekit(api_key="secret", session=session)

    client.get_library("full", page=2, per_page=50)

    assert session.calls[0]["params"] == {"page": 2, "per_page": 50}


def test_api_errors_are_raised_as_data() -> None:
    session = FakeSession(FakeResponse({"errors": [{"title": "Not found"}]}))
    client = Typekit(api_key="secret", session=session)

    with pytest.raises(TypekitAPIError) as error:
        client.get_kit("missing")

    assert error.value.errors == [{"title": "Not found"}]


def test_get_font_variations_returns_fvd_values() -> None:
    session = FakeSession(
        FakeResponse(
            {
                "family": {
                    "id": "pcpv",
                    "variations": [{"fvd": "n4"}, {"fvd": "i4"}],
                }
            }
        )
    )
    client = Typekit(api_key="secret", session=session)

    assert client.get_font_variations("pcpv") == ["n4", "i4"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"base_url": "http://example.test"}, "HTTPS"),
        ({"timeout": 0}, "greater than zero"),
    ],
)
def test_client_rejects_unsafe_configuration(kwargs: dict, message: str) -> None:
    with pytest.raises((TypekitConfigurationError, ValueError), match=message):
        Typekit(api_key="secret", **kwargs)


@pytest.mark.parametrize(
    "call",
    [
        lambda client: client.create_kit("", "example.com"),
        lambda client: client.create_kit("Example", []),
        lambda client: client.create_kit("Example", "example.com", [{}]),
        lambda client: client.create_kit(
            "Example", "example.com", [{"id": "pcpv", "subset": "invalid"}]
        ),
        lambda client: client.update_kit("abc123"),
        lambda client: client.get_library("full", page=0),
        lambda client: client.add_font("abc123", "pcpv", subset="invalid"),
    ],
)
def test_invalid_public_inputs_fail_before_network(call) -> None:
    session = FakeSession(FakeResponse({}))

    with pytest.raises(ValueError):
        call(Typekit(api_key="secret", session=session))

    assert session.calls == [], "invalid input must fail before a network request"


def test_http_and_invalid_json_failures_are_typed() -> None:
    http_client = Typekit(api_key="secret", session=FakeSession(FakeResponse({}, 401)))
    json_client = Typekit(api_key="secret", session=FakeSession(InvalidJSONResponse({})))

    with pytest.raises(TypekitAPIError) as http_error:
        http_client.list_kits()
    with pytest.raises(TypekitAPIError, match="invalid JSON"):
        json_client.list_kits()

    assert http_error.value.status_code == 401


def test_non_object_and_mapping_api_errors_are_typed() -> None:
    non_object = Typekit(api_key="secret", session=FakeSession(FakeResponse([])))
    mapping_error = Typekit(api_key="secret", session=FakeSession(FakeResponse({"errors": "bad"})))

    with pytest.raises(TypekitAPIError, match="non-object"):
        non_object.list_kits()
    with pytest.raises(TypekitAPIError) as error:
        mapping_error.list_kits()

    assert error.value.errors == ["bad"]


def test_resource_methods_use_documented_paths_and_escaped_ids() -> None:
    session = FakeSession(FakeResponse({"kit": {"families": [{"id": "pcpv"}]}}))
    client = Typekit(api_key="secret", session=session)

    client.get_published_kit("id/with/slash")
    client.remove_kit("abc123")
    client.publish_kit("abc123")
    client.list_libraries()
    client.add_font("abc123", "pcpv", variations="n4", subset="all")
    client.remove_font("abc123", "pcpv")
    assert client.get_kit_fonts("abc123") == ["pcpv"]

    assert [call["url"] for call in session.calls] == [
        "https://typekit.com/api/v1/json/kits/id%2Fwith%2Fslash/published",
        "https://typekit.com/api/v1/json/kits/abc123",
        "https://typekit.com/api/v1/json/kits/abc123/publish",
        "https://typekit.com/api/v1/json/libraries",
        "https://typekit.com/api/v1/json/kits/abc123/families/pcpv",
        "https://typekit.com/api/v1/json/kits/abc123/families/pcpv",
        "https://typekit.com/api/v1/json/kits/abc123",
    ]
    assert session.calls[4]["data"] == [("subset", "all"), ("variations", "n4")]


def test_request_and_publish_allow_per_call_timeout() -> None:
    session = FakeSession(FakeResponse({"published": "now"}))
    client = Typekit(api_key="secret", session=session, timeout=7.5)

    client.publish_kit("abc123", timeout=120)

    assert session.calls[0]["timeout"] == 120


def test_request_rejects_nonpositive_per_call_timeout_before_network() -> None:
    session = FakeSession(FakeResponse({}))
    client = Typekit(api_key="secret", session=session)

    with pytest.raises(ValueError, match="greater than zero"):
        client.request("GET", "kits", timeout=0)

    assert session.calls == []
