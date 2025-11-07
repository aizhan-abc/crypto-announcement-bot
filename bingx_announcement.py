import cloudscraper
from datetime import datetime, timezone
from bs4 import BeautifulSoup


def fetch_bingx_events():
    """
    Fetch BingX announcements (listings) via the public API.
    If API returns nothing or fails, fallback to HTML scraping.
    """
    try:
        scraper = cloudscraper.create_scraper()

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://bingx.com/",
            "Origin": "https://bingx.com",
        }

        url = "https://bingx.com/api/customer/v1/announcement/listArticles"
        params = {
            "sectionId": "11257060005007",  # Listings section
            "page": "1",
            "pageSize": "20",
        }

        response = scraper.get(url, headers=headers, params=params, timeout=15)
        text = response.text.strip()

        # Sometimes Cloudflare blocks JSON, returning HTML instead
        if not text.startswith("{"):
            print("⚠️ BingX API returned non-JSON (HTML/empty). Trying fallback scrape...")
            return _fallback_scrape(scraper)

        data = response.json()

        if not data.get("success", True):
            print("⚠️ BingX API error:", data)
            return _fallback_scrape(scraper)

        articles = data.get("data", {}).get("list", [])
        if not articles:
            print("⚠️ BingX API returned 0 events, trying fallback scrape...")
            return _fallback_scrape(scraper)

        events = []
        for article in articles:
            article_id = article.get("articleId") or article.get("id")
            article_title = article.get("title") or "Untitled"
            article_url = f"https://bingx.com/en/support/articles/{article_id}"

            events.append({
                "exchange": "BingX",
                "id": str(article_id),
                "title": article_title.strip(),
                "url": article_url,
                "pair": None,
                "kind": "listing",
                "ctime_iso": datetime.now(timezone.utc).isoformat(),
            })

        print(f"✅ BingX API fetched {len(events)} events.")
        return events

    except Exception as e:
        print("❌ BingX fetch error:", e)
        return _fallback_scrape(cloudscraper.create_scraper())


def _fallback_scrape(scraper):
    """
    Backup: scrape BingX announcements HTML page if API fails.
    """
    try:
        url = "https://bingx.com/en/support/articles/"
        r = scraper.get(url, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        events = []
        for link in soup.select("a[href*='support/articles/']"):
            href = link.get("href")
            title = link.get_text(strip=True) or link.get("title")
            if not href or not title:
                continue
            full_url = href if href.startswith("http") else "https://bingx.com" + href

            events.append({
                "exchange": "BingX",
                "id": href.split("/")[-1],
                "title": title,
                "url": full_url,
                "pair": None,
                "kind": "listing",
                "ctime_iso": datetime.now(timezone.utc).isoformat(),
            })

        print(f"🌐 BingX HTML scrape fetched {len(events)} events.")
        return events

    except Exception as e:
        print("❌ BingX HTML scrape failed:", e)
        return []
