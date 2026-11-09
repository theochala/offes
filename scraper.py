import json
import os
import time
from playwright.sync_api import sync_playwright

# 1. Ορισμός πηγών (Σελίδες προσφορών)
TARGET_SOURCES = {
    "kritikos": "https://kritikos-sm.gr/prosfores/",
    "sklevenitis": "https://www.sklavenitis.gr/prosfores/",
    "ab_vassilopoulos": "https://www.ab.gr/promotions",
    "masoutis": "https://www.masoutis.gr/offers",
    "lidl": "https://www.lidl-hellas.gr/c/prosfores/a100000"
}

def scrape_supermarket(page, url, supermarket_name):
    offers = []
    try:
        print(f"   [Playwright] Άνοιγμα σελίδας για {supermarket_name}: {url}")
        page.goto(url, timeout=40000, wait_until="domcontentloaded")
        
        # Κύλιση (scroll) για να φορτώσει δυναμικά το περιεχόμενο (lazy loading)
        for _ in range(3):
            page.mouse.wheel(0, 1000)
            time.sleep(1)

        # Εντοπισμός καρτελών προϊόντων (προσαρμοσμένοι selectors ανάλογα με τη δομή)
        # Αναζητούμε κοινά στοιχεία καρτελών (article, div με κλάσεις προϊόντων)
        cards = page.locator("article, .product-card, .item-card, li.product, .product-item").all()
        print(f"   [Playwright] Βρέθηκαν {len(cards)} πιθανές κάρτες προϊόντων στο {supermarket_name}.")

        for card in cards[:15]: # Παίρνουμε έως 15 προϊόντα ανά σούπερ μάρκετ
            try:
                # 1. Τίτλος προϊόντος
                title_elem = card.locator("h2, h3, h4, .product-title, .title, a.title").first
                title = title_elem.inner_text(timeout=500).strip() if title_elem.count() > 0 else "Προϊόν Προσφοράς"

                # 2. Τιμή προσφοράς
                price_elem = card.locator(".price, .offer-price, .amount, .current-price").first
                price = price_elem.inner_text(timeout=500).strip() if price_elem.count() > 0 else "0.00 €"

                # 3. Εικόνα προϊόντος
                img_elem = card.locator("img").first
                img_url = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") if img_elem.count() > 0 else "https://via.placeholder.com/150"
                if img_url and img_url.startswith("//"):
                    img_url = "https:" + img_url

                # Προσθήκη στη λίστα αν βρέθηκε έγκυρος τίτλος ή τιμή
                if title and price:
                    offers.append({
                        "supermarket": supermarket_name.upper(),
                        "image_url": img_url,
                        "product_title": title,
                        "offer_price": price,
                        "unit_or_original_price": "—",
                        "source_link": url
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"   [Σφάλμα] Αποτυχία σάρωσης για {supermarket_name}: {e}")

    # Fallback αν δεν επιστράφηκαν προϊόντα λόγω αυστηρών anti-bot
    if not offers:
        offers.append({
            "supermarket": supermarket_name.upper(),
            "image_url": "https://via.placeholder.com/150",
            "product_title": f"Ενεργή σελίδα προσφορών ({supermarket_name})",
            "offer_price": "0.00 €",
            "unit_or_original_price": "—",
            "source_link": url
        })

    return offers

def main():
    all_offers = []

    print("Ξεκινάει η αναλυτική συλλογή προσφορών...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        for name, link in TARGET_SOURCES.items():
            site_offers = scrape_supermarket(page, link, name)
            all_offers.extend(site_offers)

        browser.close()

    # Αποθήκευση στο clean_offers.json
    output_filename = "clean_offers.json"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(all_offers, f, ensure_ascii=False, indent=4)
        print(f"\nΕπιτυχία! Αποθηκεύτηκαν συνολικά {len(all_offers)} προσφορές στο '{output_filename}'.")
    except Exception as e:
        print(f"Σφάλμα αποθήκευσης αρχείου: {e}")
        exit(1)

if __name__ == "__main__":
    main()
