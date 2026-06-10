#!/usr/bin/env python3
"""One-time script: ask Gemini to generate macro events from 2025-01-01 to yesterday."""
import json, os, sys, datetime, urllib.request, time

GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
DASHBOARD    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS_JSON  = os.path.join(DASHBOARD, "data/events.json")
TZ           = datetime.timezone(datetime.timedelta(hours=8))

def gemini(prompt):
    url  = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096}
    }).encode()
    for attempt in range(1, 4):
        print(f"[第 {attempt} 次]", flush=True)
        try:
            req  = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
            return resp["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            if attempt < 3:
                print(f"失敗（{e}），30 秒後重試...", flush=True)
                time.sleep(30)
            else:
                raise

def main():
    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not set"); sys.exit(1)

    yesterday = (datetime.datetime.now(TZ) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    prompt = f"""請根據實際財經史實，列出 2025-01-01 至 {yesterday} 期間，對台美股市影響最大的宏觀事件。
每個月最多 2 個，挑影響最顯著的（如 Fed 決策、重大財報、地緣政治衝擊、關稅政策等）。

只輸出以下 JSON array，不加任何說明或 markdown：

[
  {{"date": "YYYY-MM-DD", "event": "事件名稱（15字內，繁體中文）"}},
  ...
]

規則：
- date 填事件實際發生日（精確到天）
- event 簡短有力，例如「Fed 降息 0.25%」「川普關稅衝擊」「NVDA 財報超預期」
- 只挑真正有發生的事件，不捏造"""

    print("讓 Gemini 生成歷史宏觀事件...", flush=True)
    raw = gemini(prompt)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])
    events = json.loads(raw.strip())
    events.sort(key=lambda x: x["date"])

    with open(EVENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"✅ 存入 {len(events)} 筆事件 → {EVENTS_JSON}")

if __name__ == "__main__":
    main()
