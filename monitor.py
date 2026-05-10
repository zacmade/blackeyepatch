import json
import os
import time
import smtplib
from email.message import EmailMessage
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# =====================================
# CONFIG
# =====================================
URLS = [
    "https://blackeyepatch.com/collections/sweat",
    "https://blackeyepatch.com/collections/tops"
]
KEYWORDS = ["jumper", "tshirt", "tee","hoodie","sweat"]
SEEN_FILE = "seen.json"
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
SEND_TO = os.environ.get("SEND_TO")
CHECK_INTERVAL = 60  # seconds

# =====================================
# LOAD SEEN PRODUCTS
# =====================================
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen = set(json.load(f))
else:
    seen = set()

# =====================================
# SETUP SELENIUM
# =====================================
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# =====================================
# FETCH PRODUCTS
# =====================================
new_products = []

for base_url in URLS:
    page = 1
    while True:
        url = f"{base_url}?page={page}"
        driver.get(url)
        time.sleep(3)  # wait for page to load

        product_elements = driver.find_elements(By.CSS_SELECTOR, 'a.full-unstyled-link')
        if not product_elements:
            break

        found_any = False
        for elem in product_elements:
            title = elem.text.strip()
            link = elem.get_attribute('href')

            lower = title.lower()
            if any(keyword in lower for keyword in KEYWORDS):
                found_any = True
                if title not in seen:
                    new_products.append((title, link))
                    seen.add(title)
        if not found_any:
            break
        page += 1

# =====================================
# SEND EMAIL ALERTS
# =====================================
if new_products:
    msg = EmailMessage()
    msg["Subject"] = "BlackEyePatch New Drop Alert"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = SEND_TO

    body = "New BlackEyePatch items detected:\n\n"
    for title, link in new_products:
        body += f"{title.title()}\n{link}\n\n"

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

# =====================================
# CLEANUP
# =====================================
driver.quit()
