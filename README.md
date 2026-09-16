# UCP Gemini Chat

A standalone Gemini-powered, Gemini-styled chat that acts as a **UCP client** — connect it to any UCP-compatible merchant and shop via natural conversation.

## Prerequisites

- Python 3.10+ (automatically installed by `uv` if not present)
- [`uv`](https://github.com/astral-sh/uv) package manager
- A Google AI Studio API key: https://aistudio.google.com
- ucpAdaptor running as the test merchant (see below)

## Quick start

### Terminal 1 — Start the test merchant (ucpAdaptor)

```bash
cd ../ucpAdaptor
export GOOGLE_API_KEY=AIza...
./mvnw spring-boot:run
# → http://localhost:8080
```

### Terminal 2 — Start the UCP Gemini Chat

```bash
cd ucpGeminiChat

# Create venv and install dependencies
uv venv --python 3.12 .venv
uv pip install -r requirements.txt

# Set your Gemini API key (or copy .env.example → .env and fill in values)
export GOOGLE_API_KEY=AIza...

# Start the app
.venv/bin/python main.py
# → http://localhost:8000
```

Open **http://localhost:8000** in your browser.

## Demo flow

1. Click the `http://localhost:8080` chip (or paste any UCP merchant URL)
2. Watch the UCP discovery + capability negotiation happen in the "Thinking" section
3. Ask to find a product: *"Find me headphones under $150"*
4. Add to cart: *"Add it to my cart"*
5. Checkout: *"I'd like to checkout"* — provide your email and address when asked
6. A payment card appears — select a method and click **Pay**
7. Order confirmation appears with your Order ID

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | required | Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Gemini model to use |
| `PORT` | `8000` | Server port |
| `PUBLIC_URL` | `http://localhost:8000` | Base URL of this agent — set to your ngrok/deployment URL when testing with external merchants |

## Architecture

```
Browser (index.html)
  ↕ SSE  POST /api/chat
FastAPI (main.py)
  ↕ Gemini function calling  (google-genai SDK)
gemini_agent.py
  ↕ MCP tool calls  (mcp library)
ucpAdaptor at http://localhost:8080/ucp/mcp
  ↕ UCP merchant tools (search, cart, checkout)
```

The chat discovers the merchant's MCP endpoint from `/.well-known/ucp`, connects with the Python MCP client, and bridges those tools to Gemini function calling. Payment is mocked in the UI.
