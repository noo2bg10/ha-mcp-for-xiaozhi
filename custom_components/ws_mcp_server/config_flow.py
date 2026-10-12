"""Config flow for the MCP Server for Xiaozhi integration."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import probatio
from yarl import URL

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.helpers import llm
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)

from .const import CONF_CLIENT_ENDPOINT, DOMAIN

_LOGGER = logging.getLogger(__name__)

MORE_INFO_URL = "https://www.home-assistant.io/integrations/mcp_server/#configuration"


def _valid_endpoint(endpoint: str) -> bool:
    """Return True if the endpoint is a ws:// or wss:// URL with a host."""
    try:
        url = URL(endpoint)
    except ValueError:
        return False
    return url.scheme in ("ws", "wss") and bool(url.host)


class WsMCPServerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Xiaozhi MCP connection."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        llm_apis = {api.id: api.name for api in llm.async_get_apis(self.hass)}

        if user_input is not None:
            endpoint = user_input[CONF_CLIENT_ENDPOINT].strip()
            api_ids = user_input.get(CONF_LLM_HASS_API) or []
            if not _valid_endpoint(endpoint):
                errors[CONF_CLIENT_ENDPOINT] = "invalid_endpoint"
            elif not api_ids:
                errors[CONF_LLM_HASS_API] = "llm_api_required"
            else:
                # Hash the endpoint: it holds a secret token and the unique id
                # is visible in the entity/diagnostic data.
                digest = hashlib.sha256(endpoint.encode()).hexdigest()[:16]
                await self.async_set_unique_id(f"{'+'.join(sorted(api_ids))}_{digest}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=", ".join(llm_apis.get(api_id, api_id) for api_id in api_ids),
                    data={
                        CONF_CLIENT_ENDPOINT: endpoint,
                        CONF_LLM_HASS_API: api_ids,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_CLIENT_ENDPOINT): TextSelector(),
                    probatio.Optional(
                        CONF_LLM_HASS_API,
                        default=[llm.LLM_API_ASSIST],
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(label=name, value=llm_api_id)
                                for llm_api_id, name in llm_apis.items()
                            ],
                            multiple=True,
                        )
                    ),
                }
            ),
            description_placeholders={"more_info_url": MORE_INFO_URL},
            errors=errors,
        )
