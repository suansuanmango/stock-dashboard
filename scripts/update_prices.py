#!/usr/bin/env python3
"""Daily price updater for investment dashboard."""

import json, os, sys, datetime, subprocess

try:
    import yfinance as yf
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance", "-q"], check=True)
    import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def taipei_now():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+08:00")

def fetch_stock(ticker_str):
    try:
        t = yf.Ticker(ticker_str)
        fi = t.fast_info
        current = fi.get("last_price") or fi.get("regularMarketPrice")
        prev = fi.get("previous_close") or fi.get("regularMarketPreviousClose")
        if not current:
            # fallback: use historical close (e.g. market closed / data unavailable)
            hist = t.history(period="5d")
            if len(hist) < 1:
                return None, None, None
            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current
        current = float(current)
        prev = float(prev) if prev else current
        change = round(current - prev, 4)
        change_pct = round((change / prev * 100) if prev else 0, 2)
        return round(current, 2), round(change, 2), change_pct
    except Exception as e:
        print(f"  ⚠ {ticker_str}: {e}")
        return None, None, None

def get_usd_twd():
    price, _, _ = fetch_stock("TWD=X")
    return price or 31.5

def update_portfolio():
    path = os.path.join(DATA_DIR, "portfolio.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rate = get_usd_twd()
    data["exchange_rate_usd_twd"] = rate
    print(f"  USD/TWD: {rate}")

    total_cost = 0
    total_value = 0

    for h in data["holdings"]:
        yf_ticker = h["ticker"] + ".TW" if h["market"] == "TW" else h["ticker"]
        price, change, change_pct = fetch_stock(yf_ticker)
        print(f"  {h['ticker']}: {price}")
        h["current_price"] = price
        h["price_change"] = change
        h["price_change_pct"] = change_pct

        qty = h.get("quantity")
        avg = h.get("avg_price")
        if price and qty and avg:
            mult = 1 if h["currency"] == "TWD" else rate
            cost = qty * avg * mult
            value = qty * price * mult
            h["current_value_twd"] = round(value)
            h["cost_twd"] = round(cost)
            h["gain_loss_twd"] = round(value - cost)
            h["gain_loss_pct"] = round((value - cost) / cost * 100, 2) if cost else 0
            total_cost += cost
            total_value += value
        else:
            h["current_value_twd"] = h["cost_twd"] = h["gain_loss_twd"] = h["gain_loss_pct"] = None

    if total_cost > 0:
        data["total_cost_twd"] = round(total_cost)
        data["total_value_twd"] = round(total_value)
        data["total_gain_loss_twd"] = round(total_value - total_cost)
        data["total_gain_loss_pct"] = round((total_value - total_cost) / total_cost * 100, 2)

    data["last_updated"] = taipei_now()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Portfolio: NT${total_value:,.0f}")

def update_watchlist():
    path = os.path.join(DATA_DIR, "watchlist.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    for s in data["stocks"]:
        yf_ticker = s["ticker"] + ".TW" if s["market"] == "TW" else s["ticker"]
        price, change, change_pct = fetch_stock(yf_ticker)
        print(f"  {s['ticker']}: {price}")
        s["current_price"] = price
        s["change"] = change
        s["change_pct"] = change_pct

    data["last_updated"] = taipei_now()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("  ✓ Watchlist saved")

def update_history():
    path = os.path.join(DATA_DIR, "history.json")
    if not os.path.exists(path):
        print("  ⚠ history.json 不存在，跳過（請先跑 init_history.py）")
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    tz = datetime.timezone(datetime.timedelta(hours=8))
    today = datetime.datetime.now(tz).strftime("%Y-%m-%d")
    indices = {"TWII": "^TWII", "GSPC": "^GSPC"}

    for key, ticker_str in indices.items():
        existing = data.get(key, {}).get("data", [])
        if existing and existing[-1]["date"] == today:
            print(f"  — {key} 今日已有數據，跳過")
            continue
        price, _, _ = fetch_stock(ticker_str)
        if price:
            existing.append({"date": today, "close": price})
            data[key]["data"] = existing
            print(f"  ✓ {key} 追加 {today}: {price}")

    data["last_updated"] = taipei_now()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def git_push():
    os.chdir(BASE_DIR)
    try:
        subprocess.run(["git", "add", "data/"], check=True, capture_output=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if diff.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", f"chore: update prices {taipei_now()[:10]}"],
                check=True, capture_output=True
            )
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print("  ✓ Pushed to GitHub")
        else:
            print("  — No changes")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ Git: {e}")

if __name__ == "__main__":
    print("📈 Updating portfolio...")
    update_portfolio()
    print("📊 Updating watchlist...")
    update_watchlist()
    print("📉 Updating history...")
    update_history()
    print("🚀 Pushing to GitHub...")
    git_push()
    print("✅ Done!")
