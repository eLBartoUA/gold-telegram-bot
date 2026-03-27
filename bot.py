import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# --- CONFIG ---
GOLDAPI_URL = "https://www.goldapi.io/api/XAU/USD"   # GoldAPI.io endpoint :contentReference[oaicite:2]{index=2}
NBU_USD_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"  # :contentReference[oaicite:3]{index=3}

TROY_OUNCE_GRAMS = 31.1034768
ASSAYS = [999, 750, 585, 550, 375]
UA_TZ = ZoneInfo("Europe/Uzhgorod")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Gold Telegram Bot)",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
}

def fetch_gold_usd_per_oz_goldapi(api_key: str) -> float:
    """
    GoldAPI.io returns XAU spot price in USD per troy ounce (field usually 'price').
    Auth via header x-access-token. :contentReference[oaicite:4]{index=4}
    """
    last_err = None
    headers = {
        **HEADERS,
        "x-access-token": api_key,
        "Content-Type": "application/json",
    }

    for attempt in range(1, 4):  # 3 tries
        try:
            r = requests.get(GOLDAPI_URL, headers=headers, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"GoldAPI temporary error: HTTP {r.status_code}")
            r.raise_for_status()

            data = r.json()

            # Prefer 'price', fallback to 'ask'/'bid'
            if "price" in data and data["price"] is not None:
                usd_per_oz = float(data["price"])
            else:
                ask = float(data.get("ask") or 0)
                bid = float(data.get("bid") or 0)
                usd_per_oz = (ask + bid) / 2 if (ask and bid) else (ask or bid)

            if not (1000 < usd_per_oz < 20000):
                raise RuntimeError(f"Bad usd_per_oz parsed: {usd_per_oz}")

            return usd_per_oz

        except Exception as e:
            last_err = e
            time.sleep(2 * attempt)

    raise RuntimeError(f"GoldAPI failed after retries: {last_err}")

def fetch_usd_uah_rate_nbu() -> float:
    r = requests.get(NBU_USD_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return float(data[0]["rate"])

def build_post(uah_per_gram_999: float, discount: float, manager: str) -> str:
    buy_uah_999 = uah_per_gram_999 * (1.0 - discount)
    date_str = datetime.now(UA_TZ).strftime("%d.%m.%Y")

    lines = [
        f"Орієнтовна ціна брухт  ЗОЛОТА на {date_str}",
        "",
    ]

    for assay in ASSAYS:
        price = buy_uah_999 * (assay / 999.0)
        lines.append(f"🔸{assay} — {int(round(price))} грн/г")

    lines += [
        "",
        "❗️Актуальна ціна залежить від виробу, стану , якості❗️",
        "💰Для отримання актуальної та найкращої  ціни зверніться до менеджера",
        "",
        f"Для звʼязку з менеджером {manager}",
        "",
        "#золото #викуп #ціназолота",
    ]
    return "\n".join(lines)

def send_to_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True
    }, timeout=30)
    resp.raise_for_status()

def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    manager = os.environ.get("MANAGER_HANDLE", "@gold_store_dp")
    discount = float(os.environ.get("DISCOUNT", "0.07"))
    goldapi_key = os.environ["GOLDAPI_KEY"]

    usd_per_oz = fetch_gold_usd_per_oz_goldapi(goldapi_key)
    usd_per_gram = usd_per_oz / TROY_OUNCE_GRAMS

    usd_uah = fetch_usd_uah_rate_nbu()
    uah_per_gram_999 = usd_per_gram * usd_uah

    post = build_post(uah_per_gram_999, discount, manager)
    send_to_telegram(token, chat_id, post)

if __name__ == "__main__":
    main()
