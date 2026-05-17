# Remander Home Assistant Integration

A Home Assistant custom integration for the Remander ESP32 firmware — a Reolink NVR away/home-mode controller.

## Status

**In planning.** This repository is waiting on a set of firmware-side enhancements before integration code is written. See the firmware-side spec at `../remander-esp32/docs/home_assistant_integration_plan.md` for the prerequisites.

## What this will do (once built)

- Auto-discover Remander devices on the local network via zeroconf.
- Expose current mode (away / home / paused) as a Home Assistant sensor.
- Expose buttons to trigger Set Away / Set Home / Pause / Rearm workflows.
- Receive activity events (workflow outcomes, mode changes, mute events) via push webhook and surface them in HA's logbook + as automation triggers.
- Provide a diagnostics download for troubleshooting.

## Installation (future)

Will be installable via [HACS](https://hacs.xyz/) as a custom repository.

## License

MIT (planned to match the firmware repo).
