#!/usr/bin/env python3
"""One-time script to backfill ^TWII and ^GSPC history from 2025-01-01."""

import json, os, sys, subprocess, datetime

try:
    import yfinance as yf
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance", "-q"], check=True)
    import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")

INDICES = {
    "TWII": {"ticker": "^TWII", "name": "台灣加權指數"},
    "GSPC": {"ticker": "^GSPC", "name": "S&P 500"},
}

def fetch_history(ticker_str, start="2025-01-01"):
    t = yf.Ticker(ticker_str)
    hist = t.history(start=start)
    rows = []
    for dt, row in hist.iterrows():
        date_str = dt.strftime("%Y-%m-%d")
        rows.append({"date": date_str, "close": round(float(row["Close"]), 2)})
    return rows

def main():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    data = {"last_updated": now}
    for key, info in INDICES.items():
        print(f"  抓取 {info['name']} ({info['ticker']})...")
        rows = fetch_history(info["ticker"])
        data[key] = {"name": info["name"], "data": rows}
        print(f"  ✓ {len(rows)} 筆")

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 存入 {HISTORY_PATH}")

if __name__ == "__main__":
    main()
