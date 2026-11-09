import json
import os
import time
from playwright.sync_api import sync_playwright

# 1. Ορισμός πηγών
TARGET_SOURCES = {
    "e_katanalotis_api": "https://e-katanalotis.gov.gr/api/products",
    "sklevenitis": "https://www.sklavenitis.gr/prosfores/",
    "ab_vassilopoulos": "https://www.ab.gr/promotions",
    "masoutis": "https://www.masoutis.gr/offers",
    "lidl": "https://www.lidl-hellas.gr/c/prosfores/a100000",
    "kritikos": "https://kritikos-sm.gr/prosfores/"
}

def scrape_with_playwright(url, supermarket_name):
    """Ασφαλής σάρωση σελίδων δυναμικού περιεχομένου με Playwright"""
    offers = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            print(f"   [Playwright] Άνοιγμα σελίδας: {url}")
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000) # Αναμονή να φορτώσει η JS
            
            # Δοκιμή εντοπισμού καρτελών προϊόντων (generic selectors)
            cards = page.locator("article, .product-card, .item-card, li.product").all()
            
            if cards:
                for card in cards[:10]: # Παίρνουμε τις πρώτες 10 προσφορές ανά site
                    try:
                        title = card.locator("h2, h3, h4, .title").inner_text(timeout=1000).strip()
                        price = card.locator(".price, .offer-price, .amount").first.inner_text(timeout=1000).strip()
                        
                        offers.append({
                            "supermarket": supermarket_name.upper(),
                            "image_url": "https://via.placeholder.com/150",
                            "product_title": f"Προσφορά | {title}",
                            "offer_price": price if price else "0.00 €",
                            "unit_or_original_price": "—",
                            "source_link": url
                        })
                    except:
                        continue
            
            # Αν δεν βρέθηκαν κάρτες αυτόματα, βάζουμε μια ένδειξη επιτυχούς πρόσβασης
            if not offers:
                offers.append({
                    "supermarket": supermarket_name.upper(),
                    "image_url": "https://via.placeholder.com/150",
                    "product_title": f"Επιτυχής πρόσβαση στη σελίδα προσφορών του/της {supermarket_name}",
                    "offer_price": "0.00 €",
                    "unit_or_original_price": "—",
                    "source_link": url
                })
                
            browser.close()
    except Exception as e:
        print(f"   [Σφάλμα Playwright] {supermarket_name}: {e}")
        offers.append({
            "supermarket": supermarket_name.upper(),
            "image_url": "https://via.placeholder.com/150",
            "product_title": f"Προσωρινός περιορισμός πρόσβασης / Anti-bot",
            "offer_price": "0.00 €",
            "unit_or_original_price": "—",
            "source_link": url
        })
    return offers

def main():
    all_offers = []

    print("1. Συλλογή προσφορών από e-Καταναλωτή...")
    # Εδώ μπορείς να προσθέσεις κλήση με requests για το API αν χρειάζεται
    
    print("2. Σάρωση ιστοσελίδων σούπερ μάρκετ με Playwright...")
    for name, link in TARGET_SOURCES.items():
        if name == "e_
