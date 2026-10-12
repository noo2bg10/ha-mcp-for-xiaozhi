"""Constants for the MCP Server for Xiaozhi integration."""

DOMAIN = "ws_mcp_server"
TITLE = "WebSocket Model Context Protocol Server"

CONF_CLIENT_ENDPOINT = "client_endpoint"

# The Stateless API is no longer registered explicitly, but this name may still exist in the
# users config entry.
STATELESS_LLM_API = "stateless_assist"

# Seconds to wait before reconnecting to the Xiaozhi endpoint after a connection ends.
RECONNECT_DELAY = 20
# Seconds between WebSocket pings that keep the connection to Xiaozhi alive.
HEARTBEAT_INTERVAL = 50

# Values of the ``ws_mcp_server.<entry_id>_status`` state.
STATUS_CONNECTING = "connecting"
STATUS_CONNECTED = "connected"
STATUS_ERROR = "error"
