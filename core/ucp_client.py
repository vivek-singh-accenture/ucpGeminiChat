import httpx

CLIENT_CAPABILITIES = [
    "dev.ucp.shopping.catalog.search",
    "dev.ucp.shopping.cart",
    "dev.ucp.shopping.checkout",
    "dev.ucp.shopping.order",
]


async def discover(merchant_url: str) -> dict:
    url = merchant_url.rstrip("/") + "/.well-known/ucp"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def extract_mcp_endpoint(profile: dict) -> str | None:
    try:
        services = profile["ucp"]["services"]
        shopping = services.get("dev.ucp.shopping", [])
        if isinstance(shopping, list):
            for svc in shopping:
                if svc.get("transport") == "mcp":
                    return svc.get("endpoint")
        elif isinstance(shopping, dict):
            if shopping.get("transport") == "mcp":
                return shopping.get("endpoint")
    except (KeyError, TypeError):
        pass
    return None


def intersect(profile: dict, client_caps: list[str] = CLIENT_CAPABILITIES) -> dict:
    try:
        raw_caps = profile["ucp"].get("capabilities", {})
        store_caps = list(raw_caps.keys()) if isinstance(raw_caps, dict) else []
    except (KeyError, TypeError):
        store_caps = []

    matched = [c for c in client_caps if c in store_caps]
    not_available = [c for c in client_caps if c not in store_caps]
    store_only = [c for c in store_caps if c not in client_caps]

    return {
        "intersection": matched,
        "store_capabilities": store_caps,
        "not_available": not_available,
        "store_only": store_only,
    }
