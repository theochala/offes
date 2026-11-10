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
    print("=== [1/3] Εκκίνηση Scraper ===")
    all_offers = []

    try:
        with sync_playwright() as p:
            print("Εκκίνηση Chromium browser...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            for market_name, url in TARGET_URLS.items():
                print(f"-> Προσπάθεια φόρτωσης {market_name}: {url}")
                try:
                    # Μείωση timeout στα 10 δευτερόλεπτα για να μην περιμένει ποτέ πολύ
                    page.goto(url, wait_until="commit", timeout=10000)
                    page.wait_for_timeout(1500)

                    market_offers = []
                    product_cards = page.locator(".product-item, .item-card, article, [data-product-id]").all()

                    if product_cards:
                        for card in product_cards[:10]:
                            try:
                                title_el = card.locator("h2, h3, .product-title, .title, a").first.inner_text()
                                price_el = card.locator(".price, .current-price, .value, span").first.inner_text()
                                old_price_el = card.locator(".old-price, .original-price, del").first.inner_text()
                                img_el = card.locator("img").first.get_attribute("src")

                                clean_title = title_el.strip() if title_el else ""
                                clean_price = price_el.strip() if price_el else ""
                                clean_old_price = old_price_el.strip() if old_price_el else ""
                                clean_img = img_el if img_el else "https://via.placeholder.com/150?text=No+Image"

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
                        print(f"  [OK] Βρέθηκαν {len(market_offers)} προϊόντα για {market_name}.")
                    else:
                        print(f"  [!] Δεν βρέθηκαν κάρτες προϊόντων στο {market_name} (πιθανό block).")

                except Exception as ex:
                    print(f"  [X] Παράκαμψη {market_name} λόγω timeout/error: {ex}")
                    continue

            browser.close()
            print("Ολοκλήρωση scraping browser.")
    except Exception as e:
        print(f"[X] Σφάλμα στο Playwright setup: {e}")

    # Δημιουργία JSON ακόμα κι αν είναι κενό, για να συνεχίσει το πρόγραμμα
    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_offers": len(all_offers),
        "offers": all_offers
    }

    filename = "clean_offers.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"=== [2/3] Δημιουργήθηκε το αρχείο {filename} με {len(all_offers)} προϊόντα. ===")
    return filename

def upload_all_to_ftp():
    print("=== [3/3] Έναρξη μεταφόρτωσης FTP ===")
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("Σφάλμα: Λείπουν τα στοιχεία FTP από τα Secrets.")
        return

    print(f"Σύνδεση στον FTP server: {ftp_server}...")
    try:
        # Πολύ αυστηρό timeout 8 δευτερολέπτων για να μην κολλάει ποτέ στο FTP
        ftp = FTP(ftp_server, timeout=8)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        print("Επιτυχής σύνδεση FTP!")

        ftp.cwd("prosfores.infy.click")
        ftp.cwd("htdocs")
        print(f"Τρέχων φάκελος FTP: {ftp.pwd()}")

        for filename in os.listdir("."):
            if os.path.isfile(filename) and not filename.startswith("."):
                if filename == "scraper.py":
                    continue

                print(f"Ανεβαίνει το αρχείο: {filename}...")
                with open(filename, "rb") as f:
                    ftp.storbinary(f"STOR {filename}", f)
                print(f"Ανέβηκε επιτυχώς: {filename}")

        ftp.quit()
        print("=== Η διαδικασία ολοκληρώθηκε με επιτυχία! ===")
    except Exception as e:
        print(f"[X] Σφάλμα σύνδεσης ή μεταφόρτωσης FTP: {e}")

if __name__ == "__main__":
    json_file = scrape_all_supermarkets()
    upload_all_to_ftp()
