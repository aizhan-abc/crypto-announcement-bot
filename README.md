# 🧠 Crypto Announcement Bot

A Python bot that monitors multiple cryptocurrency exchanges for **new listings and announcements** (Bitget, MEXC, Gate, BingX) and sends automatic updates to a **Telegram group**.

---

## 🚀 Features

- Fetches live announcements from:
  - 🟢 Bitget  
  - 🔵 MEXC  
  - 🟣 Gate.io  
  - 🟠 BingX
  - 🔵 BYBIT
  - 🟢 OKX

- Sends formatted summaries to Telegram every 5 minutes.
- Supports both **summary mode** and **new-only mode**.
- Handles duplicates automatically with a local state file.
- Built with clean modular structure for each exchange.

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/aizhan-abc/crypto-announcement-bot.git
cd crypto-announcement-bot
