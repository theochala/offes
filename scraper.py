from playwright.sync_api import sync_playwright
import json
import re
import os
import requests
from requests.auth import HTTPBasicAuth

def clean_title(title):
    artifacts = [
        "playlist_add", "favorite", "add", "remove", "Χρυσές Τιμές", 
        "Λίτ", "Τεμ", "/", "Νέο", "Προσωρινά μη διαθέσιμο", "Διαφήμιση", "με Lidl Plus", "Χωρίς Lidl Plus"
    ]
    for art in artifacts:
        title = title.replace(art, "")
    
    words = title.split()
    seen = []
    for w in words:
        if w not in seen or len(w) > 4:
            seen.append(w)
    
    title = " ".join(seen)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def parse_products(raw_products, supermarket_name):
    parsed = []
    for item in raw_products:
        text = item["text"]
        img_url = item["image"]
        
        prices = re.findall(r'(\d+[\.,]\d+\s*€)', text)
        title = text
        for price in prices:
            title = title.replace(price, "")
            
        title = clean_title(title)
        price_val = prices[-1] if prices else ""
        
        if len(title) > 5 and prices and price_val != "0,00 €" and img_url and img_url.startswith('http'):
            if not any(p['title'] == title and p['supermarket'] == supermarket_name for p in parsed):
                parsed.append({
                    "title": title,
                    "price": price_val,
                    "all_prices": prices,
                    "image": img_url,
                    "supermarket": supermarket_name
                })
    return parsed

# [Εδώ παραμένουν κανονικά οι συναρτήσεις scrape_sklavenitis, scrape_ab, scrape_masoutis, scrape_kritikos, scrape_galaxias, scrape_mymarket, scrape_lidl...]

def upload_to_wordpress(json_file="clean_offers.json"):
    if not os.path.exists(json_file):
        print("Το αρχείο clean_offers.json δεν βρέθηκε.")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        offers = json.load(f)

    wp_url = os.getenv("WP_URL", "https://prosfores.infy.click")
    wp_user = os.getenv("WP_USER")
    wp_pass = os.getenv("WP_APP_PASSWORD")

    if not wp_user or not wp_pass:
        print("Δεν βρέθηκαν τα credentials του WordPress στα GitHub Secrets. Παράλειψη ανέβασματος.")
        return

    api_url = f"{wp_url}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(wp_user, wp_pass)

    print(f"\nΞεκινάει το ανέβασμα {len(offers)} προσφορών στο WordPress...")

    for offer in offers:
        title = f"[{offer['supermarket']}] {offer['title']}"
        content = f"""
        <p><strong>Σούπερ Μάρκετ:</strong> {offer['supermarket']}</p>
        <p><strong>Τιμή:</strong> <span style="color: #d9534f; font-size: 1.3em; font-weight: bold;">{offer['price']}</span></p>
        <p><img src="{offer['image']}" alt="{offer['title']}" style="max-width:300px; height:auto; border-radius: 8px;"/></p>
        """
        
        post_data = {
            "title": title,
            "content": content,
            "status": "publish" # Δημοσιεύεται αυτόματα
        }

        try:
            response = requests.post(api_url, json=post_data, auth=auth, timeout=30)
            if response.status_code == 201:
                print(f"✔ Δημοσιεύτηκε: {title}")
            else:
                print(f"✖ Σφάλμα ({response.status_code}): {response.text[:100]}")
        except Exception as e:
            print(f"✖ Εξαίρεση κατά το ανέβασμα: {e}")

# Εκτέλεση Scraping
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    all_offers = []
    scrapers = [scrape_sklavenitis, scrape_ab, scrape_masoutis, scrape_kritikos, scrape_galaxias, scrape_mymarket, scrape_lidl]
    
    for scraper_func in scrapers:
        try:
            all_offers.extend(scraper_func(page))
        except Exception as e:
            print("Σφάλμα:", e)

    browser.close()
    
    unique_offers = []
    seen_titles = set()
    for offer in all_offers:
        key = (offer["supermarket"], offer["title"])
        if key not in seen_titles:
            seen_titles.add(key)
            unique_offers.append(offer)

    with open("clean_offers.json", "w", encoding="utf-8") as f:
        json.dump(unique_offers, f, ensure_ascii=False, indent=4)
        print(f"\nΑποθήκευση {len(unique_offers)} μοναδικών προσφορών στο clean_offers.json!")

# Αυτόματη αποστολή στο WordPress
upload_to_wordpress()
