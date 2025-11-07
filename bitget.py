# bitget_announcement.py
import time
import requests
import json

# Configuration
API_URL = "https://api.bitget.com/api/v2/public/annoucements"
LISTING_TYPE = "coin_listings"
DELISTING_TYPE = "symbol_delisting"
LANG = "en_US"
POLL_INTERVAL = 60  # seconds between checks

# State: keep track of last seen announcement ID for each type
last_seen = {
    LISTING_TYPE: None,
    DELISTING_TYPE: None
}


def fetch_announcements(ann_type, cursor=None, limit=10):
    """Fetch announcements of specific type."""
    params = {
        "language": LANG,
        "annType": ann_type,
        "limit": str(limit)
    }
    if cursor:
        params["cursor"] = cursor
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "00000":
        raise Exception(f"Unexpected API response: {data}")
    return data["data"]


def process_announcements(ann_type, ann_list):
    """Process and print new announcements in the required format."""
    global last_seen
    if not ann_list:
        return []

    formatted_announcements = []

    # Sort by creation time or ID so newest is first
    ann_list_sorted = sorted(ann_list, key=lambda x: x["cTime"])
    for ann in ann_list_sorted:
        ann_id = ann["annId"]
        # If we have a last seen id and this is not newer, skip
        if last_seen[ann_type] is not None and int(ann_id) <= int(last_seen[ann_type]):
            continue

        # Prepare formatted data
        formatted_data = {
            "exchange": "Bitget",
            "id": ann_id,
            "title": ann.get("annTitle"),
            "url": ann.get("annUrl"),
            "pair": None,
            "kind": ann_type.replace("_", " ").title(),
            "ctime_iso": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(ann.get('cTime', '0')) / 1000))
        }

        # Update last seen
        last_seen[ann_type] = ann_id

        formatted_announcements.append(formatted_data)

    return formatted_announcements


def fetch_bitget_events(language: str = "en_US"):
    """Fetch Bitget announcements for listings and delistings."""
    try:
        # Fetch and process listing events
        listing_data = fetch_announcements(LISTING_TYPE)
        formatted_listings = process_announcements(LISTING_TYPE, listing_data)

        # Fetch and process delisting events
        delisting_data = fetch_announcements(DELISTING_TYPE)
        formatted_delistings = process_announcements(DELISTING_TYPE, delisting_data)

        # Return the merged events (listings + delistings)
        return formatted_listings + formatted_delistings

    except Exception as e:
        print(f"❌ Error fetching Bitget events: {e}")
        return []

