# Brand icons

These files exist to support a PR to the [home-assistant/brands](https://github.com/home-assistant/brands) repository, which is the only canonical path for an integration logo to appear in Home Assistant's Settings → Devices & Services panel. Icons placed elsewhere in this repo are not served by the HA frontend.

## Files

- `icon.png` — 256 × 256 PNG (transparent background)
- `icon@2x.png` — 512 × 512 PNG (transparent background)

Both derive from `src/remander/static/icon-512.png` in the Python Remander repo.

## How to submit

1. Fork https://github.com/home-assistant/brands.
2. Create the directory `custom_integrations/remander/`.
3. Copy `icon.png` and `icon@2x.png` from this folder into it.
4. Open a PR titled `Add Remander custom integration`.
5. Wait for CI (image-size + transparency checks) and a maintainer review.

Once merged, `https://brands.home-assistant.io/_/remander/icon.png` becomes live and the integration logo appears automatically in any HA install — no firmware, integration, or HACS change required.
