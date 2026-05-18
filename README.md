# Remander Home Assistant Integration

A Home Assistant custom integration for the [Remander ESP32](https://github.com/hkclark/remander-esp32) Reolink NVR away/home-mode controller.

## Features

- **Zeroconf discovery** — Remander devices announcing `_remander._tcp.local.` show up automatically in Settings → Devices & Services.
- **Mode sensor** — `sensor.remander_<id>_mode` reflects `away`, `home`, or `paused`. Updated instantly via push when the device changes mode.
- **Last-workflow sensor** — State is the workflow name; attributes carry result, finished_at, duration, and any failed step.
- **Muted binary sensor** — On while a mute window is active; attributes carry `mute_until`.
- **Uptime sensor** — Seconds since the device booted (disabled by default).
- **Four command buttons** — Set Away, Set Home, Pause, Rearm. Each press POSTs to `/api/cmd/{name}`.
- **Services** — `remander.set_mode`, `remander.pause`, `remander.rearm` for YAML automations.
- **Push events** — Remander POSTs to a Home Assistant webhook on every workflow completion, mode change, mute arm/expire, or command rejection. The integration fires typed HA events (`remander_workflow_complete`, etc.) for automation triggers.
- **Diagnostics download** — Includes the most recent `/api/status` snapshot with password and webhook ID redacted.

## Requirements

- Home Assistant `2024.1.0` or newer.
- Remander ESP32 firmware with the Home Assistant integration prerequisites: `device_id` and friends in `/api/status`, multi-webhook support, schema-v2 payloads, and the `_remander._tcp` mDNS record. See `../remander-esp32/docs/home_assistant_integration_plan.md` for the firmware-side spec.

## Installation (HACS)

1. In HACS, add this repository (`https://github.com/hkclark/remander-esp32-home-assistant`) as a custom repository, category **Integration**.
2. Install "Remander" from HACS.
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → "Remander".
5. Either accept a zeroconf-discovered device or enter the host manually.

## Development

```bash
uv venv --python 3.13
uv pip install -r requirements_test.txt
.venv/bin/pytest tests/
```

## License

MIT
