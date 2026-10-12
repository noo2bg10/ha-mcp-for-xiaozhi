"""The MCP Server for Xiaozhi integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, STATUS_CONNECTING
from .session import SessionManager
from .types import WsMCPServerConfigEntry
from .websocket_transport import async_run, status_entity_id

__all__ = [
    "CONFIG_SCHEMA",
    "DOMAIN",
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (configuration is via config entries only)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WsMCPServerConfigEntry) -> bool:
    """Set up a Xiaozhi MCP connection from a config entry."""
    entry.runtime_data = SessionManager()
    status = status_entity_id(entry)
    hass.states.async_set(status, STATUS_CONNECTING)

    @callback
    def _start(hass: HomeAssistant) -> None:
        # Background tasks are cancelled automatically when the entry unloads.
        entry.async_create_background_task(
            hass, async_run(hass, entry), name=f"{DOMAIN} {entry.entry_id} connection"
        )

    # Connect once Home Assistant has finished starting (immediately if it has).
    entry.async_on_unload(async_at_started(hass, _start))
    entry.async_on_unload(entry.runtime_data.close)
    entry.async_on_unload(lambda: hass.states.async_remove(status))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: WsMCPServerConfigEntry
) -> bool:
    """Unload a config entry."""
    return True
