import json
import time
import schedule
import requests
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from okx import fetch_okx_events
from bybit import fetch_bybit_events




from bitget import fetch_bitget_events
from mexc_announcement import fetch_mexc_events
from bingx_announcement import fetch_bingx_events
from gate_api import get_announcements

# ========= CONFIG =========
TELEGRAM_TOKEN = "8314188554:AAGLiVoT3d0vQeFOXrvNoYaVuPALVv9OKJY"
CHAT_ID = "-4944185817"
SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

SEND_DELTA_ON_NEW = False
SEND_SUMMARY_EVERY_5_MIN = True
SUMMARY_WINDOW_HOURS = 24
STATE_FILE = Path("seen_ids.json")
# ==========================

import re

def sanitize_html(text: str) -> str:
    """Escape unsafe characters that break Telegram HTML parsing."""
    # Escape '<' unless part of <a> tags
    safe_text = re.sub(r'(?<!<a href=)[<](?!/a>|a )', '&lt;', text)
    safe_text = safe_text.replace('&', '&amp;').replace('>', '&gt;')
    # Fix re-escaped links back to valid form
    safe_text = safe_text.replace('&lt;a href=', '<a href=').replace('&gt;</a&gt;', '</a>')
    return safe_text

def send_telegram(html_text: str):
    """Send long Telegram messages safely (splits by lines to avoid HTML breakage)."""
    MAX_LEN = 3500  # a bit smaller to be safe

    try:
        lines = html_text.split("\n")
        current_chunk = ""
        parts = []

        for line in lines:
            # If adding this line exceeds limit, start a new chunk
            if len(current_chunk) + len(line) + 1 > MAX_LEN:
                parts.append(current_chunk)
                current_chunk = ""
            current_chunk += line + "\n"
        if current_chunk:
            parts.append(current_chunk)

        for i, part in enumerate(parts):
            if i > 0:
                time.sleep(1.5)

            r = requests.post(
                SEND_URL,
                json={
                    "chat_id": CHAT_ID,
                    "text": part,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            data = r.json()
            if not data.get("ok", False):
                print(f"⚠️ Telegram send failed (part {i+1}):", data)
            else:
                print(f"📨 Telegram part {i+1} sent successfully ({len(part)} chars).")

    except Exception as e:
        print("❌ Telegram error:", e)


def _load_seen():
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()))
        except Exception:
            return set()
    return set()


def _save_seen(seen_ids):
    try:
        STATE_FILE.write_text(json.dumps(sorted(list(seen_ids))))
    except Exception as e:
        print("⚠️ Failed to save state:", e)


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def fetch_all_events():
    """Return merged list of events from Bitget + MEXC + BingX + Gate."""
    all_events = []

    # Bitget
    try:
        bg = fetch_bitget_events(language="en_US")
        print(f"🔎 Bitget returned {len(bg)} events.")
        all_events.extend(bg)
    except Exception as e:
        print("❌ Bitget fetch error:", e)

    # MEXC
    try:
        mx = fetch_mexc_events(language="en-US")
        print(f"🔎 MEXC returned {len(mx)} events.")
        all_events.extend(mx)
    except Exception as e:
        print("❌ MEXC fetch error:", e)

    # BingX
    try:
        bx = fetch_bingx_events()
        print(f"🔎 BingX returned {len(bx)} events.")
        all_events.extend(bx)
    except Exception as e:
        print("❌ BingX fetch error:", e)
    # OKX
    try:
        okx_events = fetch_okx_events()
        print(f"🔎 OKX returned {len(okx_events)} events.")
        all_events.extend(okx_events)
    except Exception as e:
        print("❌ OKX fetch error:", e)


    # Bybit
    try:
        bybit_events = fetch_bybit_events()
        print(f"🔎 Bybit returned {len(bybit_events)} events.")
        all_events.extend(bybit_events)
    except Exception as e:
        print("❌ Bybit fetch error:", e)



    # Gate
    try:
        gate_anns = get_announcements(limit=20)
        print(f"🔎 Gate returned {len(gate_anns)} announcements.")
        for ann in gate_anns:
            all_events.append({
                "exchange": "Gate",
                "id": ann["url"],
                "title": ann["title"],
                "url": ann["url"],
                "pair": None,
                "kind": "listing",
                "ctime_iso": _iso_now(),
            })
    except Exception as e:
        print("❌ Gate fetch error:", e)

    print(f"🔎 Total merged events: {len(all_events)}")
    return all_events


def _fmt_time_utc(iso_ts: str | None):
    if not iso_ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%H:%M")
    except Exception:
        return "N/A"


def build_summary_message(events, title_prefix="ТЕСТ: НАЙДЕННЫЕ ЛИСТИНГИ"):
    """Build grouped Telegram message (like your screenshot)."""
    if not events:
        return f"📄 {title_prefix}\n—\nНет данных."

    # Filter within window
    cutoff = datetime.now(timezone.utc).timestamp() - SUMMARY_WINDOW_HOURS * 3600

    def _within_window(e):
        iso = e.get("ctime_iso")
        if not iso:
            return True
        try:
            ts = datetime.fromisoformat(iso).timestamp()
            return ts >= cutoff
        except Exception:
            return True

    events = [e for e in events if _within_window(e)]

    # Group by exchange
    by_exchange: dict[str, list] = defaultdict(list)
    for e in events:
        by_exchange[e["exchange"]].append(e)

    total = sum(len(v) for v in by_exchange.values())
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    header = [
        f"📌 {title_prefix} ЗА {today}",
        f"Всего найдено: {total}",
        "",
        "ЛИСТИНГИ (последние 24ч)",
        "---",
    ]
    lines = header

    # fixed order
    order = ["Binance", "Bybit", "OKX", "BingX", "Bitget", "MEXC", "Gate"]
    exchanges = [ex for ex in order if ex in by_exchange] + [ex for ex in by_exchange if ex not in order]

    for ex in exchanges:
        lines.append(f"{ex.upper()}")

        section = by_exchange[ex]

        # ✅ safe sorting by time
        def _safe_key(e):
            ts = e.get("ctime_iso")
            if not ts:
                return 0
            try:
                return datetime.fromisoformat(ts).timestamp()
            except Exception:
                return 0

        section = sorted(section, key=_safe_key, reverse=True)

        for it in section:
            tstr = _fmt_time_utc(it.get("ctime_iso"))
            link_text = it.get("pair") or it.get("title") or "Link"
            url = it.get("url") or "#"
            lines.append(f"  - {tstr} UTC | <a href='{url}'>{link_text}</a>")

        lines.append("")  # blank line between exchanges

    return "\n".join(lines).strip()


_seen = _load_seen()


def check_and_send():
    """Runs every 5 min: send summary and/or new listings."""
    print("⏰ Tick at", datetime.now(timezone.utc).strftime("%H:%M:%S"), "UTC")
    events = fetch_all_events()

    # Send delta (new only)
    new_items = []
    if SEND_DELTA_ON_NEW:
        for it in events:
            comp = f"{it['exchange']}:{it['id']}"
            if comp not in _seen:
                _seen.add(comp)
                new_items.append(it)
        if new_items:
            msg = build_summary_message(new_items, title_prefix="НОВЫЕ ЛИСТИНГИ")
            send_telegram(msg)
            _save_seen(_seen)
        else:
            print("📭 No new items for delta alert.")

    # Send summary (every 5m)
    if SEND_SUMMARY_EVERY_5_MIN:
        msg = build_summary_message(events, title_prefix="ТЕСТ: НАЙДЕННЫЕ ЛИСТИНГИ")
        send_telegram(msg)


def daily_midnight_summary():
    print("🗓 Daily summary at 00:00 UTC")
    events = fetch_all_events()
    msg = build_summary_message(events, title_prefix="СУТОЧНЫЙ ОТЧЕТ")
    send_telegram(msg)


def main():
    print("✅ Bot started — summary every 5 minutes.")
    send_telegram("✅ Бот запущен. Отправляю сводку каждые 5 минут.")

    # Run immediately
    check_and_send()

    # Schedule
    schedule.every(5).minutes.do(check_and_send)
    schedule.every().day.at("00:00").do(daily_midnight_summary)

    while True:
        schedule.run_pending()
        time.sleep(2)


if __name__ == "__main__":
    main()
