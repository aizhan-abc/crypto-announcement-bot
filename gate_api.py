import requests
import re
import json

def get_build_id():
    """Extract Gate.com build ID."""
    try:
        html = requests.get("https://www.gate.com/announcements", timeout=10).text
        match = re.search(r'"buildId":"(.*?)"', html)
        return match.group(1) if match else None
    except Exception as e:
        print(f"[ERROR] Failed to fetch build ID: {e}")
        return None


def get_announcements(limit=10):
    """Fetch and return latest announcements."""
    build_id = get_build_id()
    if not build_id:
        print("❌ Could not extract build ID")
        return []

    url = f"https://www.gate.com/announcements/_next/data/{build_id}/en/announcements/latest.json"
    print(f"📡 Using: {url}")

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch or parse JSON: {e}")
        return []

    try:
        items = data["pageProps"]["listData"]["list"]
    except KeyError:
        print("❌ Could not find announcements list in JSON structure.")
        return []

    results = []
    for i in items[:limit]:
        title = i.get("title", "Untitled")
        rel_time = i.get("release_time", "Unknown time")
        views = i.get("views", 0)
        raw_url = i.get("url", "")
        url = raw_url if raw_url.startswith("http") else f"https://www.gate.com{raw_url}"
        results.append({
            "title": title,
            "time": rel_time,
            "views": views,
            "url": url
        })
    return results


if __name__ == "__main__":
    anns = get_announcements(limit=10)
    if anns:
        print(f"✅ Found {len(anns)} announcements:\n")
        for a in anns:
            print(f"- {a['title']}\n  🕒 {a['time']} | 👁 {a['views']} views\n  🔗 {a['url']}\n")
    else:
        print("❌ No announcements found.")
