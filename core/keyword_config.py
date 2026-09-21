import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_CONFIG_PATH = Path("data/ucp_config.json")
_lock = asyncio.Lock()


def _ensure_file() -> None:
    _CONFIG_PATH.parent.mkdir(exist_ok=True)
    if not _CONFIG_PATH.exists():
        _CONFIG_PATH.write_text(json.dumps({"mappings": []}, indent=2))


def _normalize_url(url: str) -> str:
    url = url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _read() -> dict:
    _ensure_file()
    return json.loads(_CONFIG_PATH.read_text())


def _write(data: dict) -> None:
    _CONFIG_PATH.write_text(json.dumps(data, indent=2))


class KeywordConfig:
    async def get_all(self) -> list[dict]:
        return _read()["mappings"]

    async def add(self, keywords: list[str], url: str) -> dict:
        normalized_keywords = list(dict.fromkeys(
            k.lower().strip() for k in keywords if k.strip()
        ))
        entry = {
            "id": str(uuid.uuid4()),
            "keywords": normalized_keywords,
            "url": _normalize_url(url),
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        async with _lock:
            data = _read()
            data["mappings"].append(entry)
            _write(data)
        return entry

    async def update(self, id: str, keywords: list[str], url: str) -> dict | None:
        normalized_keywords = list(dict.fromkeys(
            k.lower().strip() for k in keywords if k.strip()
        ))
        async with _lock:
            data = _read()
            for mapping in data["mappings"]:
                if mapping["id"] == id:
                    mapping["keywords"] = normalized_keywords
                    mapping["url"] = _normalize_url(url)
                    _write(data)
                    return mapping
        return None

    async def delete(self, id: str) -> bool:
        async with _lock:
            data = _read()
            before = len(data["mappings"])
            data["mappings"] = [m for m in data["mappings"] if m["id"] != id]
            if len(data["mappings"]) < before:
                _write(data)
                return True
        return False

    def find_url_for_message(self, message: str) -> str | None:
        try:
            data = _read()
        except Exception:
            return None
        lower = message.lower()
        for mapping in data["mappings"]:
            for keyword in mapping["keywords"]:
                if keyword and keyword in lower:
                    return mapping["url"]
        return None


keyword_config = KeywordConfig()
