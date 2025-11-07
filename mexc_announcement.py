# mexc_announcement.py
import requests
from datetime import datetime, timezone

MEXC_API = "https://www.mexc.com/help/announce/api/v2/label/article/list"

# MEXC is picky about headers sometimes; use a browser UA.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

# Your working payloads
LISTING_PAYLOADS = [
    # Spot listings
    {
        "labelId": 18,
        "page": 1,
        "pageSize": 10,
        "langIso": "en-US",  # change to "ru-RU" if you prefer
        "bizType": "10",
        "sectionId": 15425930840821,
    },
    # Futures listings (if you want them)
    {
        "labelId": 18,
        "page": 1,
        "pageSize": 10,
        "langIso": "en-US",
        "bizType": "10",
        "sectionId": 15425930840822,
    },
]

DELISTING_PAYLOADS = [
    {
        "labelId": 19,
        "page": 1,
        "pageSize": 10,
        "langIso": "en-US",
        "bizType": "10",
        "sectionId": 15425930840822,
    }
]


def _ts_to_iso(ts_ms: int | None) -> str | None:
    """Convert milliseconds timestamp to ISO, if provided."""
    if not ts_ms:
        return None
    try:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _fetch_page(payload: dict) -> list[dict]:
    """Hit the MEXC endpoint once; parse data.result array."""
    payload = dict(payload)  # copy
    try:
        r = requests.post(MEXC_API, json=payload, headers=HEADERS, timeout=15)
        j = r.json()
        # MEXC uses `data.result`, not `data.list`
        items = j.get("data", {}).get("result", []) or []
        out = []
        for it in items:
            _id = str(it.get("id"))
            title = it.get("title", "")
            # Try both keys; MEXC varies
            ts = it.get("releaseTime") or it.get("publishTime") or it.get("createTime")
            out.append({
                "id": _id,
                "exchange": "MEXC",
                "title": title,
                "url": f"https://www.mexc.com/support/articles/{_id}",
                "ctime_iso": _ts_to_iso(ts),
            })
        return out
    except Exception as e:
        print("❌ Error fetching from MEXC:", e)
        return []


def fetch_mexc_events(language: str = "en-US") -> list[dict]:
    """Return normalized events (listings + delistings) from MEXC."""
    results: list[dict] = []

    # Listings
    for p in LISTING_PAYLOADS:
        p = dict(p)
        p["langIso"] = language
        for item in _fetch_page(p):
            item["kind"] = "listing"
            results.append(item)

    # Delistings
    for p in DELISTING_PAYLOADS:
        p = dict(p)
        p["langIso"] = language
        for item in _fetch_page(p):
            item["kind"] = "delisting"
            results.append(item)

    return results
