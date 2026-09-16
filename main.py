import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import config
from api.chat import router as chat_router
from api.payment import router as payment_router
from api.profile import router as profile_router

app = FastAPI(title="UCP Gemini Chat", version="1.0.0")

app.include_router(chat_router, prefix="/api")
app.include_router(payment_router, prefix="/api")
app.include_router(profile_router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    print(f"Starting UCP Gemini Chat on http://localhost:{config.PORT}")
    print(f"Model: {config.GEMINI_MODEL}")
    print(f"Agent profile: {config.PUBLIC_URL}/ucp/profile")
    if "localhost" in config.PUBLIC_URL:
        print("Tip: For external merchants (e.g. Shopify stores), run ngrok and set PUBLIC_URL=https://your-ngrok-url.ngrok.io")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
