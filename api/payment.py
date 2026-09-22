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
            result = await mcp_bridge.call_tool(
                state.mcp_endpoint,
                "complete_checkout",
                {"id": body.checkoutId},
            )

            checkout = result.get("checkout", {})
            order = result.get("order", {})

            if checkout.get("status") == "completed":
                state.checkout_status = "completed"

            # Extract order ID from the order object (spec: order is in response when completed)
            order_id = (
                order.get("id")
                or checkout.get("order_id")
                or checkout.get("orderId")
                or "N/A"
            )

            # Total from order or checkout totals (spec: array of {type, amount})
            def _find_total(totals):
                if isinstance(totals, list):
                    return next((t for t in totals if t.get("type") == "total"), {})
                elif isinstance(totals, dict):
                    return totals.get("total") or {}
                return {}

            total_obj = _find_total(order.get("totals", [])) or _find_total(checkout.get("totals", []))
            total_amount = total_obj.get("amount") or state.checkout_total_minor or 0
            total_currency = order.get("currency") or checkout.get("currency") or state.checkout_currency or "USD"

            if checkout.get("status") == "completed":
                total_display = f"${total_amount / 100:.2f} {total_currency}"
                state.history.append({
                    "role": "model",
                    "parts": [{"text": f"Your order has been placed! Order ID: {order_id}. Total: {total_display}. Thank you for shopping!"}],
                })

            # Emit normalized payload the frontend can reliably read
            normalized = {
                **result,
                "checkout": {
                    **checkout,
                    "orderId": order_id,
                    "total": {"amount": total_amount, "currency": total_currency},
                },
                "order": {
                    **order,
                    "id": order_id,
                },
            }
            yield _sse("order_confirmed", normalized)
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
