import json
import re
from typing import AsyncGenerator

from google import genai
from google.genai import types

import config
from core.keyword_config import keyword_config
from core.session import ConversationState
from core.ucp_client import discover, extract_mcp_endpoint, intersect
from tools.definitions import REQUEST_PAYMENT_TOOL
from transport import mcp_bridge

_client = genai.Client(api_key=config.GOOGLE_API_KEY)

_SYSTEM_PROMPT = """You are a UCP Shopping Assistant — a helpful AI that shops at UCP-compatible websites on behalf of the user.

WORKFLOW:
1. DISCOVERY: When the user provides a merchant URL, discovery happens automatically. You will see a system note confirming the connection and available tools. Acknowledge it naturally.

2. SEARCH: Always search the catalog before recommending products. Never invent product details. After calling search_catalog, do NOT list or describe the products in your text — the UI renders them as cards automatically. Just say something brief like "Here's what I found — let me know which one you'd like!" and stop. Never repeat product names, prices, or IDs in your reply.

3. CART: Create a cart first (the first time items are added). Remember the cart ID. Add items using the cart ID and product/merchandise ID.

4. CHECKOUT:
   a. When the user wants to checkout, ask for their email address and full shipping address if not already provided.
   b. Create a checkout using the cart ID.
   c. Update the checkout with buyer email and shipping address.
   d. When the response shows the checkout is ready to complete, call request_payment with the total and checkout ID.
   e. Do NOT complete the checkout yourself — the payment UI handles that.

5. After payment succeeds, the order confirmation will appear automatically.

ERROR HANDLING: If a tool returns an error, do NOT retry with different parameters. Report the error to the user immediately and stop. If the error mentions a connection failure, advise the user to start a new chat and connect to http://localhost:8080 for the local demo.

STYLE: Be concise and conversational. When showing products, use a simple list. Do not describe your internal tool calls — just present results naturally."""

_GENERAL_PROMPT = """You are a helpful shopping assistant with access to Google Search. \
Answer product questions, compare items, give recommendations, and help users research what they want to buy. \
Be concise and conversational."""

_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _clean_schema(schema: dict, remove_meta: bool = True) -> dict:
    """Recursively clean a JSON Schema for Gemini compatibility.
    Removes unsupported keys and optionally strips the 'meta' field.
    """
    UNSUPPORTED = {"$schema", "additionalProperties", "format", "$defs", "examples", "default"}
    result = {}
    for k, v in schema.items():
        if k in UNSUPPORTED:
            continue
        if k == "properties" and isinstance(v, dict):
            cleaned = {}
            for prop_name, prop_schema in v.items():
                if remove_meta and prop_name == "meta":
                    continue
                cleaned[prop_name] = _clean_schema(prop_schema, remove_meta=False)
            result["properties"] = cleaned
        elif k == "required" and isinstance(v, list):
            filtered = [r for r in v if not (remove_meta and r == "meta")]
            if filtered:
                result["required"] = filtered
        elif k == "items" and isinstance(v, dict):
            result["items"] = _clean_schema(v, remove_meta=False)
        elif isinstance(v, dict):
            result[k] = _clean_schema(v, remove_meta=False)
        else:
            result[k] = v
    return result


def _mcp_tools_to_gemini(mcp_tools: list[dict]) -> list[types.FunctionDeclaration]:
    """Convert raw MCP tool dicts to Gemini FunctionDeclarations, stripping 'meta'."""
    declarations = []
    for tool in mcp_tools:
        raw_schema = tool.get("input_schema") or tool.get("inputSchema") or {"type": "object"}
        cleaned = _clean_schema(raw_schema, remove_meta=True)
        try:
            params = types.Schema.model_validate(cleaned)
        except Exception:
            params = types.Schema(type="OBJECT")
        declarations.append(types.FunctionDeclaration(
            name=tool["name"],
            description=tool.get("description", ""),
            parameters=params,
        ))
    return declarations


def _build_genai_config(merchant_tools: list[dict], has_merchant: bool) -> types.GenerateContentConfig:
    if not has_merchant:
        return types.GenerateContentConfig(
            system_instruction=_GENERAL_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )

    if merchant_tools:
        function_declarations = _mcp_tools_to_gemini(merchant_tools) + [REQUEST_PAYMENT_TOOL]
    else:
        from tools.definitions import UCP_TOOLS
        function_declarations = UCP_TOOLS

    return types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=function_declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _update_state(state: ConversationState, tool_name: str, result: dict) -> None:
    checkout = result.get("checkout", {})
    cart = result.get("cart", {})

    if cart.get("id"):
        state.cart_id = cart["id"]
    if checkout.get("id"):
        state.checkout_id = checkout["id"]
    if checkout.get("status"):
        state.checkout_status = checkout["status"]

    total = checkout.get("total", {})
    if total.get("amount") is not None:
        state.checkout_total_minor = total["amount"]
    if total.get("currency"):
        state.checkout_currency = total["currency"]

    if result.get("cartId") and not state.cart_id:
        state.cart_id = result["cartId"]


async def run_turn(state: ConversationState, user_message: str) -> AsyncGenerator[str, None]:
    # Detect merchant URL on first mention
    if state.mcp_endpoint is None and state.merchant_url is None:
        keyword_matched_url = keyword_config.find_url_for_message(user_message)
        if keyword_matched_url:
            state.merchant_url = keyword_matched_url
        else:
            match = _URL_PATTERN.search(user_message)
            if match:
                state.merchant_url = match.group(0).rstrip("/.,)")

    # Run UCP discovery if we have a merchant URL but no profile yet
    if state.merchant_url and state.ucp_profile is None:
        try:
            profile = await discover(state.merchant_url)
            state.ucp_profile = profile
            mcp_ep = extract_mcp_endpoint(profile)
            state.mcp_endpoint = mcp_ep

            cap_result = intersect(profile)
            state.capabilities_intersection = cap_result["intersection"]

            ucp_version = profile.get("ucp", {}).get("version", "unknown")
            yield _sse("ucp_discovery", {
                "merchantUrl": state.merchant_url,
                "ucpVersion": ucp_version,
                "mcpEndpoint": mcp_ep,
                "storeCapabilities": cap_result["store_capabilities"],
            })
            yield _sse("ucp_intersection", {
                "intersection": cap_result["intersection"],
                "storeOnly": cap_result["store_only"],
                "notAvailable": cap_result["not_available"],
            })

            # Fetch merchant's native MCP tools for dynamic Gemini binding
            state.merchant_tools = await mcp_bridge.list_tools(mcp_ep)

            tool_names = [t["name"] for t in state.merchant_tools]
            caps_str = ", ".join(cap_result["intersection"]) or "none"
            state.history.append({
                "role": "user",
                "parts": [{"text": (
                    f"[SYSTEM] Successfully connected to {state.merchant_url} "
                    f"(UCP {ucp_version}). MCP endpoint: {mcp_ep}. "
                    f"Shared capabilities: {caps_str}. "
                    f"Available tools: {', '.join(tool_names)}."
                )}],
            })
            state.history.append({
                "role": "model",
                "parts": [{"text": (
                    f"Connected to {state.merchant_url}! This store supports UCP and I can "
                    f"search products, manage your cart, and process checkout. "
                    f"What would you like to find?"
                )}],
            })
        except Exception as exc:
            yield _sse("text", {"chunk": f"I couldn't connect to that URL: {exc}. Please check the address and try again."})
            yield _sse("done", {})
            return

    # Add user message to history
    state.history.append({"role": "user", "parts": [{"text": user_message}]})

    # Build Gemini config (uses merchant tools if available, else static UCP tools)
    genai_config = _build_genai_config(state.merchant_tools, has_merchant=bool(state.mcp_endpoint))

    # Agent loop — keep going until no more function calls (max 8 rounds)
    for _round in range(8):
        accumulated_parts = []
        function_calls: list[types.FunctionCall] = []

        try:
            stream = await _client.aio.models.generate_content_stream(
                model=config.GEMINI_MODEL,
                contents=state.history,
                config=genai_config,
            )
            async for chunk in stream:
                if not chunk.candidates:
                    continue
                candidate = chunk.candidates[0]
                if not candidate.content or not candidate.content.parts:
                    continue

                for part in candidate.content.parts:
                    if part.text:
                        accumulated_parts.append(part)
                        yield _sse("text", {"chunk": part.text})
                    elif part.function_call:
                        fc = part.function_call
                        function_calls.append(fc)
                        accumulated_parts.append(part)  # preserve thought_signature for thinking models
        except Exception as exc:
            yield _sse("text", {"chunk": f"\n\nError: {exc}"})
            yield _sse("done", {})
            return

        # Record model turn
        if accumulated_parts:
            state.history.append({"role": "model", "parts": accumulated_parts})

        # No function calls — we're done
        if not function_calls:
            break

        # Execute function calls and feed results back
        tool_response_parts = []
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            yield _sse("tool_use", {"name": fc.name, "arguments": args})

            # Intercept payment signal — do not call MCP for this
            if fc.name == "request_payment":
                yield _sse("payment_request", {
                    "total_minor_units": args.get("total_minor_units", state.checkout_total_minor),
                    "currency": args.get("currency", state.checkout_currency),
                    "checkout_id": args.get("checkout_id", state.checkout_id),
                })
                yield _sse("done", {})
                return

            if not state.mcp_endpoint:
                result = {"error": "No merchant connected. Please provide a UCP merchant URL first."}
            else:
                try:
                    result = await mcp_bridge.call_tool(state.mcp_endpoint, fc.name, args)
                    _update_state(state, fc.name, result)
                except Exception as exc:
                    result = {"error": str(exc)}

            yield _sse("tool_result", {"name": fc.name, "result": result})
            tool_response_parts.append({
                "function_response": {
                    "name": fc.name,
                    "response": result,
                }
            })

        # Add tool results and loop back to Gemini
        state.history.append({"role": "user", "parts": tool_response_parts})

    yield _sse("done", {})
