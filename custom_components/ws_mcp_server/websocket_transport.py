"""WebSocket transport that connects Home Assistant to a Xiaozhi MCP endpoint.

Unlike the core ``mcp_server`` integration (where an MCP client connects to
Home Assistant), Xiaozhi hands out a WebSocket "access point" URL. Home
Assistant dials out to it and acts as the MCP *server* over that socket.

The endpoint URL contains a secret token in its query string, so it must never
reach the logs. Use :func:`redact_endpoint` / :func:`scrub` for anything that
is logged or shown.
"""

import asyncio
import logging

import aiohttp
import anyio
from mcp import types
from mcp.shared.message import SessionMessage
from yarl import URL

from homeassistant.components import conversation
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import llm

from .const import (
    CONF_CLIENT_ENDPOINT,
    DOMAIN,
    HEARTBEAT_INTERVAL,
    RECONNECT_DELAY,
    STATUS_CONNECTED,
    STATUS_CONNECTING,
    STATUS_ERROR,
)
from .server import create_server
from .session import Session
from .types import WsMCPServerConfigEntry

_LOGGER = logging.getLogger(__name__)


def status_entity_id(entry: WsMCPServerConfigEntry) -> str:
    """Return the entity id of the connection status state for an entry."""
    return f"{DOMAIN}.{entry.entry_id}_status".lower()


def redact_endpoint(endpoint: str) -> str:
    """Return only the scheme, host and port of an endpoint (no path/token)."""
    try:
        return str(URL(endpoint).origin())
    except (ValueError, TypeError):
        return "<invalid endpoint>"


def scrub(text: object, endpoint: str) -> str:
    """Remove the secret endpoint (and its token) from text before logging."""
    result = str(text)
    if not endpoint:
        return result
    result = result.replace(endpoint, redact_endpoint(endpoint))
    try:
        query = URL(endpoint).query_string
    except ValueError:
        query = ""
    if query:
        result = result.replace(query, "***")
    return result


async def async_run(hass: HomeAssistant, entry: WsMCPServerConfigEntry) -> None:
    """Keep the connection to the Xiaozhi endpoint alive until cancelled."""
    endpoint: str = entry.data[CONF_CLIENT_ENDPOINT]
    status = status_entity_id(entry)
    while True:
        hass.states.async_set(status, STATUS_CONNECTING)
        try:
            await _connect_to_client(hass, entry, endpoint)
            _LOGGER.info(
                "Connection to %s closed; reconnecting in %s s",
                redact_endpoint(endpoint),
                RECONNECT_DELAY,
            )
            hass.states.async_set(status, STATUS_CONNECTING)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - must keep the loop alive
            hass.states.async_set(status, STATUS_ERROR)
            _LOGGER.warning(
                "Connection to %s failed: %s; retrying in %s s",
                redact_endpoint(endpoint),
                scrub(err, endpoint),
                RECONNECT_DELAY,
            )
        await asyncio.sleep(RECONNECT_DELAY)


async def _connect_to_client(
    hass: HomeAssistant, entry: WsMCPServerConfigEntry, endpoint: str
) -> None:
    """Connect to the Xiaozhi endpoint and serve MCP until the socket closes."""
    session_manager = entry.runtime_data
    status = status_entity_id(entry)

    llm_context = llm.LLMContext(
        platform=DOMAIN,
        context=Context(),
        language="*",
        assistant=conversation.DOMAIN,
        device_id=None,
    )
    server = await create_server(hass, entry.data[CONF_LLM_HASS_API], llm_context)
    options = await hass.async_add_executor_job(server.create_initialization_options)

    read_stream_writer, read_stream = anyio.create_memory_object_stream[
        SessionMessage | Exception
    ](0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream[
        SessionMessage
    ](0)

    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30)
    async with (
        read_stream_writer,
        read_stream,
        write_stream,
        write_stream_reader,
        session_manager.create(Session(read_stream_writer)),
        aiohttp.ClientSession(timeout=timeout) as client_session,
    ):
        _LOGGER.debug("Connecting to %s", redact_endpoint(endpoint))
        async with client_session.ws_connect(endpoint) as ws:
            _LOGGER.info("Connected to %s", redact_endpoint(endpoint))
            hass.states.async_set(status, STATUS_CONNECTED)

            async def ws_reader() -> None:
                """Forward messages from the socket to the MCP server."""
                try:
                    async for msg in ws:
                        if msg.type is not aiohttp.WSMsgType.TEXT:
                            continue
                        try:
                            message = types.JSONRPCMessage.model_validate_json(
                                msg.data
                            )
                        except ValueError as err:
                            _LOGGER.warning("Ignoring invalid MCP message: %s", err)
                            continue
                        _LOGGER.debug("MCP message received: %s", message)
                        await read_stream_writer.send(SessionMessage(message))
                finally:
                    _LOGGER.debug("WebSocket reader finished")
                    tg.cancel_scope.cancel()

            async def ws_writer() -> None:
                """Forward messages from the MCP server to the socket."""
                try:
                    async for session_message in write_stream_reader:
                        _LOGGER.debug("MCP message sent: %s", session_message)
                        await ws.send_str(
                            session_message.message.model_dump_json(
                                by_alias=True, exclude_none=True
                            )
                        )
                finally:
                    tg.cancel_scope.cancel()

            async def heartbeat() -> None:
                """Ping periodically; leave (and thus reconnect) if it fails."""
                try:
                    while True:
                        await asyncio.sleep(HEARTBEAT_INTERVAL)
                        _LOGGER.debug("Sending WebSocket ping")
                        await ws.ping()
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("WebSocket ping failed: %s", scrub(err, endpoint))
                finally:
                    tg.cancel_scope.cancel()

            async with anyio.create_task_group() as tg:
                tg.start_soon(ws_reader)
                tg.start_soon(ws_writer)
                tg.start_soon(heartbeat)
                try:
                    await server.run(read_stream, write_stream, options)
                finally:
                    # Whichever side ends first tears down the connection so
                    # the reconnect loop can start a fresh one right away.
                    tg.cancel_scope.cancel()
