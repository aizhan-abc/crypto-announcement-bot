import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re

def fetch_okx_events():
    try:
        scraper = cloudscraper.create_scraper()
        urls = [
            ("listing", "https://www.okx.com/help/section/announcements-new-listings"),
            ("delisting", "https://www.okx.com/help/section/announcements-delistings"),
        ]
        events = []
        for kind, url in urls:
            print(f"🌐 Fetching OKX {kind} announcements...")
            resp = scraper.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"⚠️ OKX page error {resp.status_code} for {kind}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Select all anchor tags that lead to individual announcement pages
            links = soup.select("a[href*='/help/']")
            if not links:
                print(f"⚠️ No OKX {kind} links found.")
                continue

            count_before = len(events)
            for a in links:
                title = a.get_text(strip=True)
                href = a.get("href")

                if not title or not href:
                    continue

                # Filter for relevant titles only
                lower = title.lower()
                if not any(word in lower for word in ["list", "launch", "delist", "remove", "trading pair"]):
                    continue

                # Normalize full URL and ID
                full_url = href if href.startswith("http") else f"https://www.okx.com{href}"
                article_id = re.sub(r"[^0-9a-zA-Z]", "", href.split("/")[-1])

                events.append({
                    "exchange": "OKX",
                    "id": article_id,
                    "title": title,
                    "url": full_url,
                    "pair": None,
                    "kind": kind,
                    "ctime_iso": datetime.now(timezone.utc).isoformat(),
                })

            print(f"📑 OKX {kind}: {len(events) - count_before} filtered events")

        print(f"✅ OKX total: {len(events)} listing/delisting events.")
        return events

    except Exception as e:
        print("❌ OKX fetch error:", e)
        return []
