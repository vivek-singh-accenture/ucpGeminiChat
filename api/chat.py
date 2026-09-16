from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.gemini_agent import run_turn
from core.session import store

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversationId: str


@router.post("/chat")
async def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    state = store.get_or_create(body.conversationId)

    async def event_stream():
        async for event in run_turn(state, body.message):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
