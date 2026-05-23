"""
Black Eyepatch New Outfit Monitor
==================================
Monitors only the Sweatshirt and Tees collections.
Designed for GitHub Actions — runs once per trigger, no loop.
known_products.json is committed back to the repo by the workflow
so it persists between runs.
"""

import requests
import json
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ──────────────────────────────────────────────
#  CONFIGURATION — set these as GitHub Secrets
# ──────────────────────────────────────────────
CONFIG = {
    "GMAIL_ADDRESS":      os.environ["GMAIL_ADDRESS"],
    "GMAIL_APP_PASSWORD": os.environ["GMAIL_APP_PASSWORD"],
    "NOTIFY_EMAIL":       os.environ["NOTIFY_EMAIL"],
}

# Only these two collections are monitored
COLLECTION_URLS = [
    "https://blackeyepatch.com/en/collections/sweat/products.json?limit=250",
    "https://blackeyepatch.com/en/collections/tees/products.json?limit=250",
]

KNOWN_PRODUCTS_FILE = "known_products.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_products() -> list[dict]:
    """Fetch all products from both monitored collections, deduplicated."""
    seen_ids = set()
    all_products = []
    for base_url in COLLECTION_URLS:
        page = 1
        while True:
            url  = f"{base_url}&page={page}"
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            data = resp.json().get("products", [])
            if not data:
                break
            for p in data:
                if str(p["id"]) not in seen_ids:
                    seen_ids.add(str(p["id"]))
                    all_products.append(p)
            if len(data) < 250:
                break
            page += 1
    return all_products


def load_known_ids() -> set[str]:
    if not os.path.exists(KNOWN_PRODUCTS_FILE):
        return set()
    with open(KNOWN_PRODUCTS_FILE) as f:
        return set(json.load(f))


def save_known_ids(ids: set[str]) -> None:
    with open(KNOWN_PRODUCTS_FILE, "w") as f:
        json.dump(sorted(ids), f, indent=2)


def send_email(new_products: list[dict]) -> None:
    subject = f"🆕 Black Eyepatch: {len(new_products)} New Item{'s' if len(new_products) > 1 else ''} Dropped!"

    items_html = ""
    for p in new_products:
        handle   = p.get("handle", "")
        title    = p.get("title", "Unknown")
        url      = f"https://blackeyepatch.com/en/products/{handle}"
        images   = p.get("images") or []
        img_src  = images[0].get("src", "") if images else ""
        img_tag  = f'<img src="{img_src}" width="200" style="border-radius:8px;margin-bottom:8px;" /><br/>' if img_src else ""
        variants = p.get("variants") or []
        price    = f"${variants[0]['price']}" if variants else ""
        items_html += f"""
        <div style="margin:20px 0;padding:16px;border:1px solid #ddd;border-radius:10px;max-width:320px;font-family:sans-serif;">
            {img_tag}
            <strong style="font-size:16px;">{title}</strong><br/>
            <span style="color:#555;">{price}</span><br/>
            <a href="{url}" style="display:inline-block;margin-top:10px;padding:8px 16px;background:#111;color:#fff;text-decoration:none;border-radius:6px;">Shop Now →</a>
        </div>
        """

    html = f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:auto;">
        <h2 style="border-bottom:2px solid #111;padding-bottom:8px;">Black Eyepatch Drop Alert 🏴</h2>
        <p>New item(s) just appeared in Sweatshirts or Tees:</p>
        {items_html}
        <p style="color:#aaa;font-size:12px;margin-top:30px;">
            Detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ·
            <a href="https://blackeyepatch.com/en/collections/sweat">Sweatshirts</a> ·
            <a href="https://blackeyepatch.com/en/collections/tees">Tees</a>
        </p>
    </body></html>
    """

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = CONFIG["GMAIL_ADDRESS"]
    msg["To"]      = CONFIG["NOTIFY_EMAIL"]
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(CONFIG["GMAIL_ADDRESS"], CONFIG["GMAIL_APP_PASSWORD"])
        server.sendmail(CONFIG["GMAIL_ADDRESS"], CONFIG["NOTIFY_EMAIL"], msg.as_string())

    log.info(f"Email sent for {len(new_products)} new product(s).")


def check_once() -> None:
    log.info("Checking Black Eyepatch sweatshirts + tees...")
    products    = fetch_products()
    known_ids   = load_known_ids()
    current_ids = {str(p["id"]) for p in products}

    if not known_ids:
        save_known_ids(current_ids)
        log.info(f"First run: saved {len(current_ids)} known products as baseline. No email sent.")
        return

    new_ids = current_ids - known_ids
    if not new_ids:
        log.info("No new products found.")
        save_known_ids(current_ids)
        return

    new_products = [p for p in products if str(p["id"]) in new_ids]
    log.info(f"Found {len(new_products)} new product(s) — sending email.")
    send_email(new_products)
    save_known_ids(current_ids)


if __name__ == "__main__":
    check_once()
