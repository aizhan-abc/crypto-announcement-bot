import requests
from datetime import datetime, timezone


def fetch_bybit_events():
    """
    Fetch Bybit announcements (listings & delistings) directly from the public API.
    Works for spot listings, derivatives, and delistings.
    """
    try:
        base_url = "https://api.bybit.com/v5/announcements/index"
        params = {
            "locale": "en-US",
            "limit": 20
        }

        resp = requests.get(base_url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("retCode") != 0:
            print("⚠️ Unexpected Bybit API response:", data)
            return []

        articles = data.get("result", {}).get("list", [])
        events = []

        for article in articles:
            title = article.get("title", "")
            url = f"https://announcements.bybit.com/en-US/article/{article.get('id')}" if article.get("id") else "https://announcements.bybit.com/en-US/"

            # Determine if it’s a listing or delisting
            lower_title = title.lower()
            if "list" in lower_title or "launch" in lower_title:
                kind = "listing"
            elif "delist" in lower_title or "remove" in lower_title:
                kind = "delisting"
            else:
                kind = "announcement"

            events.append({
                "exchange": "Bybit",
                "id": article.get("id"),
                "title": title,
                "url": url,
                "pair": None,
                "kind": kind,
                "ctime_iso": datetime.now(timezone.utc).isoformat(),
            })

        print(f"✅ Bybit fetched {len(events)} announcements.")
        return events

    except Exception as e:
        print("❌ Bybit fetch error:", e)
        return []
