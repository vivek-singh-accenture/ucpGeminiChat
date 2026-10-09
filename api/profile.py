from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

_BASE = "https://ucp.dev/2026-08-25"

_AGENT_PROFILE = {
    "ucp": {
        "version": "2026-08-25",
        "services": {},
        "capabilities": {
            "dev.ucp.shopping.catalog.search": [
                {
                    "version": "2026-08-25",
                    "spec": f"{_BASE}/specification/shopping/catalog/",
                    "schema": f"{_BASE}/schemas/shopping/catalog_search.json",
                }
            ],
            "dev.ucp.shopping.cart": [
                {
                    "version": "2026-08-25",
                    "spec": f"{_BASE}/specification/shopping/cart/",
                    "schema": f"{_BASE}/schemas/shopping/cart.json",
                }
            ],
            "dev.ucp.shopping.checkout": [
                {
                    "version": "2026-08-25",
                    "spec": f"{_BASE}/specification/shopping/checkout/",
                    "schema": f"{_BASE}/schemas/shopping/checkout.json",
                }
            ],
            "dev.ucp.shopping.order": [
                {
                    "version": "2026-08-25",
                    "spec": f"{_BASE}/specification/shopping/order/",
                    "schema": f"{_BASE}/schemas/shopping/order.json",
                }
            ],
        },
        "payment_handlers": {},
    },
}


@router.get("/ucp/profile")
async def agent_profile():
    return JSONResponse(
        content=_AGENT_PROFILE,
        headers={"Cache-Control": "public, max-age=3600"},
    )
