import json
import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

import config

_TIMEOUT = 15.0


def _agent_profile_url() -> str:
    return f"{config.PUBLIC_URL}/ucp/profile"


async def list_tools(mcp_endpoint: str) -> list[dict]:
    """Fetch tool schemas from an MCP endpoint. Returns list of raw tool dicts."""
    # Try Streamable HTTP first
    try:
        with anyio.fail_after(_TIMEOUT):
            async with streamable_http_client(mcp_endpoint) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [t.model_dump() for t in result.tools]
    except Exception:
        pass

    # Fallback: plain JSON-RPC
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.post(mcp_endpoint, json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {},
            })
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {}).get("tools", [])
    except Exception:
        return []


async def call_tool(mcp_endpoint: str, tool_name: str, tool_args: dict) -> dict:
    # Try Streamable HTTP first (Spring AI / ucpAdaptor)
    try:
        with anyio.fail_after(_TIMEOUT):
            async with streamable_http_client(mcp_endpoint) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, tool_args)
                    if result.content and result.content[0].text:
                        return json.loads(result.content[0].text)
                    return {"error": "Empty response from MCP server"}
    except Exception:
        pass  # fall through to plain JSON-RPC

    # Fallback: plain JSON-RPC 2.0 POST (fondouk.dev, mellow-monkey, etc.)
    try:
        return await _call_tool_jsonrpc(mcp_endpoint, tool_name, tool_args)
    except Exception as exc:
        cause = exc
        if hasattr(exc, "exceptions") and exc.exceptions:
            cause = exc.exceptions[0]
        return {"error": f"MCP connection failed: {cause}"}


async def _call_tool_jsonrpc(mcp_endpoint: str, tool_name: str, tool_args: dict) -> dict:
    """Plain JSON-RPC POST — no SSE/streaming, no initialize handshake required."""
    # Inject UCP agent meta if not already present (required by some MCP servers)
    args = dict(tool_args)
    if "meta" not in args:
        args["meta"] = {"ucp-agent": {"profile": _agent_profile_url()}}

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.post(mcp_endpoint, json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        })
        resp.raise_for_status()

        data = resp.json()
        if "error" in data:
            return {"error": data["error"].get("message", str(data["error"]))}

        content = data.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                return {"text": content[0]["text"]}

        return data.get("result", {})
