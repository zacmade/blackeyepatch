import json
import os
import requests
import smtplib
from email.message import EmailMessage

# =====================================
# CONFIG
# =====================================

PRODUCTS_URL = "https://blackeyepatch.com/products.json?limit=250"

KEYWORDS = [
    "hoodie",
    "jumper",
    "crewneck",
    "sweatshirt",
]

SEEN_FILE = "seen.json"

# EMAIL SETTINGS
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
SEND_TO = os.environ["SEND_TO"]

# =====================================
# LOAD SEEN PRODUCTS
# =====================================

if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen = set(json.load(f))
else:
    seen = set()

# =====================================
# FETCH PRODUCTS
# =====================================

response = requests.get(PRODUCTS_URL, timeout=20)
products = response.json()["products"]

new_products = []

for product in products:
    title = product["title"]
    handle = product["handle"]

    lower = title.lower()

    if any(keyword in lower for keyword in KEYWORDS):
        if title not in seen:
            link = f"https://blackeyepatch.com/products/{handle}"
            new_products.append((title, link))
            seen.add(title)

# =====================================
# SEND EMAIL ALERTS
# =====================================

if new_products:
    msg = EmailMessage()

    msg["Subject"] = "BlackEyePatch New Drop Alert"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = SEND_TO

    body = "New BlackEyePatch items detected:

"

    for title, link in new_products:
        body += f"{title}
{link}

"

    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print("Email alert sent")

# =====================================
# SAVE UPDATED PRODUCTS
# =====================================

with open(SEEN_FILE, "w") as f:
    json.dump(list(seen), f)
