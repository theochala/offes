import json
import os
from datetime import datetime
from ftplib import FTP
from playwright.sync_api import sync_playwright

TARGET_URLS = {
    "Μασούτης": "https://www.masoutis.gr/offers",
    "Σκλαβενίτης": "https://www.sklavenitis.gr/sylloges/prosfores/",
    "Lidl": "https://www.lidl-hellas.gr/c/store/evdomadiaies-epiloges-26kw45/a10106403",
    "MyMarket": "https://www.mymarket.gr/offers?srsltid=AYCX9vJAEuUd6A9J70LsUgVl9eSugbCgIdwLfjS928We_Oc2AeBL0hoP",
    "ΑΒ Βασιλόπουλος": "https://www.ab.gr/search/promotions"
}

def scrape_all_supermarkets():
    print("=== [1/3] Εκκίνηση Scraper με Anti-Bot Stealth ===")
    all_offers = []

    try:
        with sync_playwright() as p:
            # Χρησιμοποιούμε κανονικό headful/headless mode με επιπλέον arguments για απόκρυψη αυτοματισμού
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized"
                ]
            )
            
            # Δημιουργία context με ρεαλιστικά χαρακτηριστικά browser (User-Agent, γλώσσα, viewport)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="el-GR",
                timezone_id="Europe/Athens"
            )
            
            # Απόκρυψη του navigator.webdriver για να μην το εντοπίζουν τα bot blockers
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            
            page = context.new_page()

            for market_name, url in TARGET_URLS.items():
                print(f"-> Φόρτωση σελίδας {market_name}: {url}")
                try:
                    # Μετάβαση στη σελίδα και αναμονή να φορτώσει πλήρως
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    
                    # Προσομοίωση κίνησης χρήστη (scroll για να φορτώσουν οι εικόνες και τα προϊόντα)
                    page.mouse.wheel(0, 500)
                    page.wait_for_timeout(3000)

                    market_offers = []
                    
                    # Ευρύτεροι selectors για να πιάσουμε τις κάρτες προϊόντων ανάλογα το site
                    product_cards = page.locator(".product-item, .item-card, article, [data-product-id], .product-card").all()

                    if not product_cards:
                        # Εναλλακτική αναζήτηση αν αλλάζει η δομή
                        product_cards = page.locator("div[class*='product'], li[class*='product']").all()

                    print(f"  [i] Εντοπίστηκαν {len(product_cards)} υποψήφια στοιχεία στο {market_name}.")

                    for card in product_cards[:15]: # Παίρνουμε έως 15 προϊόντα ανά μάρκα
                        try:
                            # Δοκιμή εξαγωγής τίτλου
                            title_el = card.locator("h2, h3, .product-title, .title, a[title], .name").first.inner_text()
                            # Δοκιμή εξαγωγής τιμής προσφοράς
                            price_el = card.locator(".price, .current-price, .value, span[class*='price']").first.inner_text()
                            # Δοκιμή παλιάς τιμής
                            old_price_el = card.locator(".old-price, .original-price, del, span[class*='old']").first.inner_text()
                            # Εικόνα προϊόντος
                            img_el = card.locator("img").first.get_attribute("src")

                            clean_title = title_el.strip() if title_el else ""
                            clean_price = price_el.strip() if price_el else ""
                            clean_old_price = old_price_el.strip() if old_price_el else ""
                            clean_img = img_el if img_el else ""

                            # Αν βρέθηκε έγκυρος τίτλος και τιμή που περιέχει αριθμό
                            if len(clean_title) > 2 and any(char.isdigit() for char in clean_price):
                                market_offers.append({
                                    "supermarket": market_name,
                                    "title": clean_title,
                                    "price": clean_price,
                                    "old_price": clean_old_price,
                                    "image": clean_img,
                                    "date": datetime.now().strftime("%Y-%m-%d")
                                })
                        except:
                            continue

                    if market_offers:
                        all_offers.extend(market_offers)
                        print(f"  [OK] Επιτυχής εξαγωγή {len(market_offers)} προϊόντων από {market_name}.")
                    else:
                        print(f"  [!] Δεν εξήχθησαν προϊόντα από {market_name} (αποτροπή από bot filter).")

                except Exception as ex:
                    print(f"  [X] Σφάλμα ή timeout στο {market_name}: {ex}")
                    continue

            browser.close()
    except Exception as e:
        print(f"[X] Σφάλμα λειτουργίας Playwright: {e}")

    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_offers": len(all_offers),
        "offers": all_offers
    }

    filename = "clean_offers.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"=== [2/3] Δημιουργήθηκε το αρχείο {filename} με συνολικά {len(all_offers)} προϊόντα. ===")
    return filename

def upload_all_to_ftp():
    print("=== [3/3] Μεταφόρτωση στο FTP ===")
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("Σφάλμα: Λείπουν τα στοιχεία FTP.")
        return

    try:
        ftp = FTP(ftp_server, timeout=10)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        ftp.cwd("prosfores.infy.click")
        ftp.cwd("htdocs")

        for filename in os.listdir("."):
            if os.path.isfile(filename) and not filename.startswith("."):
                if filename == "scraper.py":
                    continue
                with open(filename, "rb") as f:
                    ftp.storbinary(f"STOR {filename}", f)
                print(f"Ανέβηκε: {filename}")

        ftp.quit()
        print("=== Η διαδικασία ολοκληρώθηκε! ===")
    except Exception as e:
        print(f"[X] Σφάλμα FTP: {e}")

if __name__ == "__main__":
    scrape_all_supermarkets()
    upload_all_to_ftp()
