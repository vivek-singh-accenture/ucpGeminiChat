from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

_AGENT_PROFILE = {
    "ucp": {
        "version": "2026-08-25",
        "capabilities": [
            {"id": "dev.ucp.shopping.catalog.search", "version": "2026-08-25"},
            {"id": "dev.ucp.shopping.cart", "version": "2026-08-25"},
            {"id": "dev.ucp.shopping.checkout", "version": "2026-08-25"},
        ],
    },
    "payment": {
        "handlers": [
            {
                "id": "mock_payment",
                "name": "Mock Payment (Demo)",
                "version": "2026-08-25",
            }
        ]
    },
}


@router.get("/ucp/profile")
async def agent_profile():
    return JSONResponse(content=_AGENT_PROFILE)
