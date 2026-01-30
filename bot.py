import os
import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

GOLDPRICE_URL = "https://goldprice.org/"  # золото ТІЛЬКИ звідси
NBU_USD_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"

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

def fetch_gold_usd_per_gram() -> float:
    r = requests.get(GOLDPRICE_API_USD, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()

    xau_oz_usd = float(data["items"][0]["xauPrice"])  # USD за 1 тройську унцію
    return xau_oz_usd / TROY_OUNCE_GRAMS  # USD за 1 грам


def fetch_usd_uah_rate_nbu() -> float:
    r = requests.get(NBU_USD_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return float(data[0]["rate"])

def build_post(uah_per_gram_999: float, discount: float, manager: str) -> str:
    buy_uah_999 = uah_per_gram_999 * (1.0 - discount)
    date_str = datetime.now(UA_TZ).strftime("%d.%m.%Y")

    lines = [f"Актуальна ціна викупа ЗОЛОТА на {date_str}\n"]
    for assay in ASSAYS:
        price = buy_uah_999 * (assay / 999.0)
        lines.append(f"{assay} — {int(round(price))} грн/г")

    lines += [
        "\nНайкраща і актуальна ціна на золото\n",
        f"для звʼязку з менеджером {manager}\n",
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
