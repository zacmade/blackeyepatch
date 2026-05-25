"""
Black Eyepatch New Outfit Monitor
Monitors Sweatshirt and Tees collections.
Designed for GitHub Actions — runs once per trigger.
known_products.json is committed back to repo to persist between runs.
"""

import requests
import json
import smtplib
import os
import time
import logging
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

CONFIG = {
    "GMAIL_ADDRESS":      os.environ["GMAIL_ADDRESS"],
    "GMAIL_APP_PASSWORD": os.environ["GMAIL_APP_PASSWORD"],
    "NOTIFY_EMAIL":       os.environ["NOTIFY_EMAIL"],
}

COLLECTIONS = [
    {"name": "Sweatshirts", "url": "https://blackeyepatch.com/en/collections/sweat"},
    {"name": "Tees",        "url": "https://blackeyepatch.com/en/collections/tees"},
]

KNOWN_PRODUCTS_FILE = "known_products.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_products() -> list[dict]:
    """Scrape product handles from collection pages."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    all_products = []
    seen_handles = set()

    for collection in COLLECTIONS:
        url  = f"{collection['url']}?page=1"
        resp = requests.get(url, headers=headers, timeout=15)
        html = resp.text
        log.info(f"Fetched {url} — status {resp.status_code}, size {len(html)} bytes")

        handles = re.findall(r'href="(/en/products/([^"?#/]+))"', html)
        log.info(f"Found {len(handles)} raw handle matches for {collection['name']}")

        for full_path, handle in handles:
            if handle not in seen_handles:
                seen_handles.add(handle)
                all_products.append({
                    "id":         handle,
                    "handle":     handle,
                    "title":      handle.replace("-", " ").title(),
                    "url":        f"https://blackeyepatch.com{full_path}",
                    "collection": collection["name"],
                })
        time.sleep(2)

    log.info(f"Found {len(all_products)} total products across collections.")
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
        url   = p.get("url", f"https://blackeyepatch.com/en/products/{p['handle']}")
        title = p.get("title", p["handle"])
        coll  = p.get("collection", "")
        items_html += f"""
        <div style="margin:20px 0;padding:16px;border:1px solid #ddd;border-radius:10px;max-width:320px;font-family:sans-serif;">
            <strong style="font-size:16px;">{title}</strong><br/>
            <span style="color:#888;font-size:13px;">{coll}</span><br/>
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

    if not current_ids:
        log.warning("No products found at all — possible block or site change. Skipping save.")
        return

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
