# MCP Server for Xiaozhi

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=noo2bg10&repository=ha-mcp-for-xiaozhi&category=integration)

A Home Assistant custom integration that exposes Home Assistant to the
[Xiaozhi AI](https://xiaozhi.me) voice assistant over the Model Context
Protocol (MCP). Home Assistant connects **outbound** to your Xiaozhi MCP
access point (a WebSocket URL) and serves its tools over that socket, so no
proxy, port forwarding or extra server is needed.

## Features

- Home Assistant acts as the MCP server and dials out to Xiaozhi via WebSocket.
- Tools come from Home Assistant's own LLM APIs (the same ones as the built-in
  `mcp_server` integration): **Assist** and any other registered LLM API.
  Select several APIs in one entry.
- Multiple entries (e.g. several Xiaozhi agents) are supported.
- Automatic reconnect, keep-alive pings, and a status state
  `ws_mcp_server.<entry_id>_status` (`connecting` / `connected` / `error`).
- The secret access point URL is never written to the logs.

## Requirements

- Home Assistant **2026.10.0** or newer.
- [HACS](https://hacs.xyz).
- A Xiaozhi MCP access point URL (`wss://…`) from the Xiaozhi console.

## Installation

1. In HACS, open **⋮ → Custom repositories**, add
   `https://github.com/noo2bg10/ha-mcp-for-xiaozhi` with type **Integration**
   (or use the badge above).
2. Download **MCP Server for Xiaozhi** and restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & services → Add integration** and choose
   **MCP Server for Xiaozhi**.
2. Paste the Xiaozhi MCP access point URL (`ws://` or `wss://`).
3. Choose the LLM APIs to expose. **Assist** is Home Assistant's built-in API;
   the other options are other LLM APIs registered in Home Assistant.
4. Submit, wait a minute, and refresh the Xiaozhi access point page: the tools
   should be listed.

> The access point URL contains a secret token. Treat it like a password and
> don't paste it into issues or screenshots.

## Usage and troubleshooting

- The Assist API only exposes entities you have exposed in
  **Settings → Voice assistants → Expose**. Expose (and name clearly) what you
  want Xiaozhi to control.
- Scripts exposed to Assist also become tools.
- If something doesn't behave, first check Xiaozhi's chat log to see whether it
  called a Home Assistant tool at all.
- If a Home Assistant tool was called, enable debug logging to see the exchange:

  ```yaml
  logger:
    logs:
      custom_components.ws_mcp_server: debug
  ```

## Credits and license

Forked from [c1pher-cn/ha-mcp-for-xiaozhi](https://github.com/c1pher-cn/ha-mcp-for-xiaozhi),
updated for current Home Assistant releases. Released under the
[MIT License](LICENSE); the original copyright notice is retained.
