import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.session import store
from transport import mcp_bridge

router = APIRouter()


class PaymentConfirmRequest(BaseModel):
    conversationId: str
    checkoutId: str


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/payment/confirm")
async def confirm_payment(body: PaymentConfirmRequest):
    state = store.get(body.conversationId)
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not state.mcp_endpoint:
        raise HTTPException(status_code=400, detail="No merchant connected")

    async def event_stream():
        try:
            # Use merchant's actual tool name (ucpAdaptor: checkout_complete; others may differ)
            tool_names = {t["name"] for t in (state.merchant_tools or [])}
            if "complete_checkout" in tool_names:
                complete_tool = "complete_checkout"
                complete_args = {"id": body.checkoutId}
            else:
                complete_tool = "checkout_complete"
                complete_args = {"checkoutId": body.checkoutId}

            result = await mcp_bridge.call_tool(
                state.mcp_endpoint,
                complete_tool,
                complete_args,
            )

            checkout = result.get("checkout", {})
            if checkout.get("status") == "completed":
                state.checkout_status = "completed"

                # Add order confirmation to conversation history
                order_id = checkout.get("orderId", "N/A")
                total = checkout.get("total", {})
                total_display = f"${total.get('amount', 0) / 100:.2f} {total.get('currency', 'USD')}"
                state.history.append({
                    "role": "model",
                    "parts": [{"text": f"Your order has been placed! Order ID: {order_id}. Total: {total_display}. Thank you for shopping!"}],
                })

            yield _sse("order_confirmed", result)
        except Exception as exc:
            yield _sse("order_confirmed", {"error": str(exc)})

        yield _sse("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
