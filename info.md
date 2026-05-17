# Remander

Home Assistant integration for the [Remander ESP32](https://github.com/kclark/remander-esp32) Reolink NVR away/home-mode controller.

## Features

- Zeroconf auto-discovery on the local network
- Sensor for current mode (away / home / paused)
- Buttons to trigger Set Away / Set Home / Pause / Rearm workflows
- Push-driven activity events (workflow outcomes, mode changes, mute events) via Home Assistant webhooks
- Diagnostics download for support

## Requirements

- Remander ESP32 firmware with the Home Assistant integration prerequisites (`device_id` in `/api/status`, multi-webhook support, schema-v2 payloads, `_remander._tcp` mDNS).
