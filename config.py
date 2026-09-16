import os
import sys
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
PORT = int(os.getenv("PORT", "8000"))
# PUBLIC_URL: set to your ngrok/deployment URL when testing with external merchants.
# External merchants will try to fetch this URL to validate the UCP agent profile.
PUBLIC_URL = os.getenv("PUBLIC_URL", f"http://localhost:{PORT}").rstrip("/")

if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY environment variable is required.", file=sys.stderr)
    print("Get your API key at https://aistudio.google.com", file=sys.stderr)
    sys.exit(1)
