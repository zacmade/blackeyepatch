"""
Run this once to print the raw HTML of the collection page
so we can see what product link format BEP uses.
"""
import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})

resp = session.get("https://blackeyepatch.com/en/collections/tees?page=1", timeout=15)
print(f"Status: {resp.status_code}")
print(f"Size: {len(resp.text)} bytes")
print("\n--- FIRST 5000 CHARS ---")
print(resp.text[:5000])
print("\n--- SEARCHING FOR 'products' in HTML ---")
import re
matches = re.findall(r'href="([^"]*product[^"]*)"', resp.text)
print(f"Found {len(matches)} href matches containing 'product':")
for m in matches[:20]:
    print(" ", m)
