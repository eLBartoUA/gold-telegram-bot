import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ── Налаштування ──────────────────────────────────────────────
GOLDPRICE_API = "https://data-asg.goldprice.org/dbXRates/USD"
NBU_USD_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
TROY_OUNCE_GRAMS = 31.1034768

ASSAYS = [999, 750, 585, 550, 375]
UA_TZ = ZoneInfo("Europe/Uzhgorod")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://goldprice.org/",
    "Origin": "https://goldprice.org",
}


# ── Отримання ціни золота з goldprice.org API ─────────────────
def fetch_gold_usd_per_gram() -> float:
    """
    Використовуємо внутрішній API goldprice.org
    Повертає ціну USD за 1 грам чистого золота (999 проба).
    """
    last_err = None

    for attempt in range(1, 4):
        try:
            r = requests.get(GOLDPRICE_API, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()

            # API повертає: {"items": [{"xauPrice": 3350.42, ...}]}
            items = data.get("items")
            if not items:
                raise RuntimeError(f"API відповідь без 'items': {data}")

            xau_price = float(items[0]["xauPrice"])

            if xau_price <= 0:
                raise RuntimeError(f"xauPrice <= 0: {xau_price}")

            usd_per_gram = xau_price / TROY_OUNCE_GRAMS
            print(f"[OK] Gold spot: ${xau_price:.2f}/oz = ${usd_per_gram:.2f}/g")
            return usd_per_gram

        except Exception as e:
            last_err = e
            print(f"[WARN] Спроба {attempt}/3 не вдалась: {e}")
            time.sleep(3 * attempt)

    raise RuntimeError(f"Не вдалось отримати ціну з goldprice.org API: {last_err}")


# ── Курс USD/UAH від НБУ ─────────────────────────────────────
def fetch_usd_uah_rate_nbu() -> float:
    r = requests.get(NBU_USD_URL, headers={
        "User-Agent": HEADERS["User-Agent"]
    }, timeout=30)
    r.raise_for_status()
    data = r.json()
    rate = float(data[0]["rate"])
    print(f"[OK] NBU USD/UAH: {rate}")
    return rate


# ── Формування поста ──────────────────────────────────────────
def build_post(uah_per_gram_999: float, discount: float, manager: str) -> str:
    buy_uah_999 = uah_per_gram_999 * (1.0 - discount)
    date_str = datetime.now(UA_TZ).strftime("%d.%m.%Y")

    lines = [
        f"Орієнтовна ціна брухт ЗОЛОТА на {date_str}",
    ]

    for assay in ASSAYS:
        price = buy_uah_999 * (assay / 999.0)
        lines.append(f" 🔸{assay} — {int(round(price))} грн/г")

    lines += [
        "❗️Актуальна ціна залежіть від виробу, стану , якості❗️",
        "💰Для отримання актуальної та найкращої ціни зверниться до менеджера"
        f" Для звʼязку з менеджером {manager}",
        "",
        "#золото #викуп #ціназолота",
    ]

    return "\n".join(lines)


# ── Відправка в Telegram ──────────────────────────────────────
def send_to_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }, timeout=30)
    resp.raise_for_status()
    print("[OK] Пост відправлено в Telegram!")


# ── Головна функція ───────────────────────────────────────────
def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    manager = os.environ.get("MANAGER_HANDLE", "@gold_store_dp")
    discount = float(os.environ.get("DISCOUNT", "0.20"))

    print(f"Дисконт: {discount * 100:.0f}%")
    print(f"Менеджер: {manager}")

    gold_usd = fetch_gold_usd_per_gram()
    usd_uah = fetch_usd_uah_rate_nbu()

    gold_uah_999 = gold_usd * usd_uah
    print(f"Золото 999: {gold_uah_999:.2f} грн/г (до дисконту)")

    post = build_post(gold_uah_999, discount, manager)
    print(f"\n--- ПОСТ ---\n{post}\n--- КІНЕЦЬ ---\n")

    send_to_telegram(token, chat_id, post)


if __name__ == "__main__":
    main()
