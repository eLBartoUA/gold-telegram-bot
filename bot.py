import os
import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

NBU_USD_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
GOLDPRICE_TODAY_URL = "https://goldprice.org/gold-price-today"
TROY_OUNCE_GRAMS = 31.1034768

ASSAYS = [999, 750, 585, 550, 375]
UA_TZ = ZoneInfo("Europe/Uzhgorod")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Gold Telegram Bot)",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
}

def to_float(num_str: str) -> float:
    return float(num_str.replace(",", "").strip())

GOLDPRICE_URL = "https://goldprice.org/"
NBU_USD_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"

GOLDPRICE_API_USD = "https://data-asg.goldprice.org/dbXRates/USD"
TROY_OUNCE_GRAMS = 31.1034768

GOLDPRICE_TODAY_URL = "https://goldprice.org/gold-price-today"
TROY_OUNCE_GRAMS = 31.1034768

def fetch_gold_usd_per_gram() -> float:
    r = requests.get(
        GOLDPRICE_TODAY_URL,
        headers={**HEADERS, "Referer": "https://goldprice.org/"},
        timeout=30
    )
    r.raise_for_status()
    html = r.text

    # прибираємо script/style (там купа чисел) і всі HTML-теги
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # ловимо саме рядок: "Gold Price 5345.64 -38.66 -0.72%"
    m = re.search(
        r"\bGold Price\b(?!\s*Today)\s+([0-9][0-9,]*\.[0-9]+)\s+"
        r"[+-][0-9][0-9,]*\.[0-9]+\s+[+-]?[0-9][0-9,]*\.[0-9]+%",
        cleaned,
        re.IGNORECASE
    )
    if not m:
        raise RuntimeError("Не зміг витягнути Gold Price з gold-price-today")

    usd_per_oz = float(m.group(1).replace(",", ""))
    return usd_per_oz / TROY_OUNCE_GRAMS

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
    manager = os.environ.get("MANAGER_HANDLE", "@gridr")
    discount = float(os.environ.get("DISCOUNT", "0.20"))

    gold_usd = fetch_gold_usd_per_gram()
    usd_uah = fetch_usd_uah_rate_nbu()

    gold_uah_999 = gold_usd * usd_uah
    post = build_post(gold_uah_999, discount, manager)
    send_to_telegram(token, chat_id, post)

if __name__ == "__main__":
    main()
