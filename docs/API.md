---
this_file: docs/API.md
---

# Adobe Fonts API map

The service and URL paths retain the Typekit name even though the product is now Adobe Fonts. The authoritative documentation is the [Adobe Fonts Typekit API reference](https://fonts.adobe.com/docs/api).

## Authentication and transport

Create the credential on Adobe’s official [API Token page](https://fonts.adobe.com/account/tokens). Adobe requires authenticated requests to use HTTPS. `typekit2` sends `TYPEKIT_API_KEY` as `X-Typekit-Token`, following the [authentication reference](https://fonts.adobe.com/docs/api/auth). It deliberately avoids the documented query-string fallback because URLs are commonly retained in logs and traces.

Form bodies follow Adobe’s [parameter encoding](https://fonts.adobe.com/docs/api/parameters): repeated values use `name[]`, while family objects use keys such as `families[0][id]`.

## Client methods

| Python method | HTTP endpoint | Notes |
|---|---|---|
| `list_kits()` | `GET kits` | Authenticated user’s kits |
| `get_kit(id)` | `GET kits/:kit` | Current draft |
| `get_published_kit(id)` | `GET kits/:kit/published` | CDN-published version |
| `create_kit(...)` | `POST kits` | Creates a draft |
| `update_kit(...)` | `POST kits/:kit` | Supplied fields replace their current values |
| `remove_kit(id)` | `DELETE kits/:kit` | Permanent deletion |
| `publish_kit(id)` | `POST kits/:kit/publish` | Asynchronous publish |
| `add_font(...)` | `POST kits/:kit/families/:family` | Adds or replaces one family |
| `remove_font(...)` | `DELETE kits/:kit/families/:family` | Removes one family |
| `get_font_family(id)` | `GET families/:family` | IDs and slugs are accepted by Adobe |
| `get_font_variations(id)` | `GET families/:family` | Extracts FVD codes from the response |
| `list_libraries()` | `GET libraries` | Available font libraries |
| `get_library(...)` | `GET libraries/:library` | Supports `page` and `per_page` |

## Safe CLI workflows

- `kit-fonts` returns compact family records and supports substring filtering across IDs, slugs, and names.
- `plan-remove-fonts` resolves every requested ID, slug, or name before writing and returns the projected count.
- `remove-fonts` issues narrow family DELETEs, then compares the complete before/after ID sets to prove unrelated families remain.
- `remove-fonts --publish=true` publishes only after draft verification. Network errors are reconciled against current draft/published state because a mutating timeout has an indeterminate outcome.
- `request-get` is a read-only raw escape hatch; raw POST or DELETE calls are intentionally not exposed.

Reference pages: [kit manipulation](https://fonts.adobe.com/docs/api/kits), [font families](https://fonts.adobe.com/docs/api/v1/:format/families/:family), [libraries](https://fonts.adobe.com/docs/api/v1/:format/libraries), and [errors](https://fonts.adobe.com/docs/api/errors).

## Important semantics

- Draft changes are not live until `publish_kit` is called.
- Publishing returns before CDN propagation finishes.
- When an update parameter is supplied, Adobe replaces that parameter’s existing value.
- Font variations use Font Variation Description codes such as `n4` and `i7`.
- `subset` is either `default` or `all`.
- The legacy analytics option is deprecated by Adobe and is intentionally not exposed.

The upstream documentation is old in vocabulary but remains live and dated © 2026. `typekit2` documents only behavior supported by those current pages.
