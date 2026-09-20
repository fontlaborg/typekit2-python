---
this_file: README.md
---

# typekit2

`typekit2` is a modern Python client and Fire CLI for the Adobe Fonts API formerly known as the Typekit API.

It replaces the abandoned `typekit` package’s Python 2 code and `setup.py` packaging with Python 3.10+, `pyproject.toml`, HTTPS header authentication, `.env` support, offline tests, and Git-tag-derived versions.

## Install

```bash
uv add typekit2
```

For local development:

```bash
uv sync
```

Create `.env` from the supplied example, or export the key directly:

```bash
cp .env.example .env
export TYPEKIT_API_KEY='your-token'
```

`python-dotenv` loads `.env` without overriding an existing environment variable. Never commit `.env`; it is ignored.

## Python API

```python
from typekit2 import Typekit

client = Typekit()  # reads TYPEKIT_API_KEY

kits = client.list_kits()
family = client.get_font_family("pcpv")
variations = client.get_font_variations("pcpv")
library = client.get_library("full", page=1, per_page=50)
```

An explicit key is also supported:

```python
client = Typekit(api_key="...")
```

The compatibility keyword `api_token=` is accepted, but new code should use `api_key=` or `TYPEKIT_API_KEY`.

### Kit workflow

```python
created = client.create_kit(
    "Example",
    ["example.com", "www.example.com"],
    [{"id": "pcpv", "subset": "all", "variations": ["n4", "i4"]}],
)
kit_id = created["kit"]["id"]

client.update_kit(kit_id, name="Example renamed")
client.add_font(kit_id, "gkmg", variations=["n4", "n7"])
client.publish_kit(kit_id)
```

Publishing is asynchronous. Adobe documents that CDN propagation may take several minutes.

## CLI

The installed `typekit2` command and `python -m typekit2` expose the same Fire CLI. Results are stable JSON.

```bash
typekit2 doctor
typekit2 kits
typekit2 kit abc123
typekit2 kit abc123 --published=true
typekit2 family pcpv
typekit2 variations pcpv
typekit2 libraries
typekit2 library full --page=1 --per-page=50
```

Mutating commands are explicit:

```bash
typekit2 create-kit Example --domains=example.com,www.example.com
typekit2 add-font abc123 pcpv --variations=n4,i4 --subset=all
typekit2 update-kit abc123 --name='Renamed kit'
typekit2 publish-kit abc123
typekit2 remove-font abc123 pcpv
typekit2 remove-kit abc123
```

For `--families`, pass a JSON list:

```bash
typekit2 create-kit Example \
  --domains=example.com \
  --families='[{"id":"pcpv","subset":"all","variations":["n4","i4"]}]'
```

Run `typekit2 --help` or `python -m typekit2 --help` for generated Fire help.

## API behavior

- Requests use `https://typekit.com/api/v1/json`.
- Authentication uses the documented `X-Typekit-Token` header; keys never enter URLs or CLI output.
- Kit writes use URL-encoded Rails-style nested parameters.
- A 30-second timeout is applied by default and can be changed with `Typekit(timeout=...)`.
- HTTP, JSON, and documented API errors raise `TypekitAPIError`.
- `update_kit` sends only supplied fields; omitted fields are not replaced accidentally.

See [docs/API.md](docs/API.md) for the method-to-endpoint map and links to Adobe’s authoritative documentation.

## Development

```bash
./test.sh
```

The suite is offline: it uses request doubles and never creates, publishes, or deletes a real kit.

## Releases

Versions come from Git tags through `hatch-vcs`; generated `typekit2/__version__.py` is explicitly ignored. To validate, commit/tag/push the next semantic version, build fresh distributions, and publish with `uv`:

```bash
./publish.sh
```

Set `PUBLISH_SKIP_UPLOAD=1` to exercise the Git release and artifact verification flow without uploading to PyPI. `UV_PUBLISH_TOKEN` supplies a PyPI token when Trusted Publishing is unavailable.

## License and provenance

MIT. The project began as `typekit-python` by Suchan Lee; `typekit2` is its Python 3 modernization.
