"""Constants for the Remander integration."""

from __future__ import annotations

DOMAIN = "remander"

CONF_HOST = "host"
CONF_PASSWORD = "password"
CONF_WEBHOOK_ID = "webhook_id"
CONF_DEVICE_ID = "device_id"

WEBHOOK_TAG = "home_assistant"
WEBHOOK_SCHEMA = "v2"
WEBHOOK_EVENTS = [
    "workflow_complete",
    "mode_changed",
    "mute_armed",
    "mute_expired",
    "command_rejected",
]

DEFAULT_POLL_INTERVAL_SECONDS = 30
DEFAULT_TIMEOUT_SECONDS = 10

MANUFACTURER = "Remander"
MODEL = "remander-esp32"

EVENT_WORKFLOW_COMPLETE = "remander_workflow_complete"
EVENT_MODE_CHANGED = "remander_mode_changed"
EVENT_MUTE_ARMED = "remander_mute_armed"
EVENT_MUTE_EXPIRED = "remander_mute_expired"
EVENT_COMMAND_REJECTED = "remander_command_rejected"
