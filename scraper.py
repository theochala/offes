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
    print("=== [1/3] Εκκίνηση Ευέλικτου Scraper ===")
    all_offers = []

    try:
        with sync_playwright() as p:
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
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="el-GR",
                timezone_id="Europe/Athens"
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            page = context.new_page()

            for market_name, url in TARGET_URLS.items():
                print(f"-> Φόρτωση σελίδας {market_name}: {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Scroll για φόρτωση lazy loading
                    for _ in range(3):
                        page.mouse.wheel(0, 1500)
                        page.wait_for_timeout(1500)

                    market_offers = []

                    # Πιο ευρύς εντοπισμός στοιχείων (όλα τα articles, divs και list items)
                    cards = page.locator("article, div[class*='product'], div[class*='card'], div[class*='item'], li[class*='product'], li[class*='item']").all()
                    print(f"  [i] Εντοπίστηκαν {len(cards)} υποψήφια στοιχεία στο {market_name}.")

                    for card in cards[:40]: # Εξέταση έως 40 στοιχείων ανά μάρκα
                        try:
                            title_text = ""
                            price_text = ""
                            old_price_text = ""
                            img_src = ""

                            # 1. Βρες οποιοδήποτε κείμενο τίτλου (από h2, h3, a, span με κλάσεις τίτλου)
                            all_texts = card.locator("h2, h3, h4, a, span, p").all_inner_texts()
                            
                            possible_titles = []
                            possible_prices = []

                            for txt in all_texts:
                                t = txt.strip()
                                if not t:
                                    continue
                                # Αν περιέχει € ή σύμβολο τιμής και αριθμό, το θεωρούμε τιμή
                                if any(char.isdigit() for char in t) and ('€' in t or '£' in t or ',' in t or '.' in t) and len(t) < 10:
                                    if not price_text:
                                        price_text = t
                                # Αλλιώς, αν είναι αρκετά μεγάλο για τίτλο προϊόντος
                                elif len(t) > 5 and not any(w in t.lower() for w in ["καλάθι", "σούπερ", "αρχική", "σύνδεση", "προσφορές"]):
                                    possible_titles.append(t)

                            # Επιλέγουμε τον μεγαλύτερο/καλύτερο τίτλο από τους διαθέσιμους
                            if possible_titles:
                                title_text = max(possible_titles, key=len)

                            # Αν δεν βρήκε τιμή με το παραπάνω, δοκιμάζουμε πιο στοχευμένα
                            if not price_text:
                                p_el = card.locator("[class*='price'], [class*='amount'], span").all_inner_texts()
                                for pt in p_el:
                                    if any(char.isdigit() for char in pt) and ('€' in pt or len(pt) < 6):
                                        price_text = pt.strip()
                                        break

                            # Εικόνα
                            img_el = card.locator("img").first
                            if img_el.count() > 0:
                                src = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                                if src and src.startswith("http"):
                                    img_src = src

                            # Αν βρέθηκαν έγκυρα στοιχεία
                            if title_text and price_text:
                                if not any(o['title'] == title_text for o in market_offers):
                                    market_offers.append({
                                        "supermarket": market_name,
                                        "title": title_text,
                                        "price": price_text,
                                        "old_price": old_price_text,
                                        "image": img_src if img_src else "https://via.placeholder.com/150?text=Offer",
                                        "date": datetime.now().strftime("%Y-%m-%d")
                                    })
                        except:
                            continue

                    if market_offers:
                        all_offers.extend(market_offers)
                        print(f"  [OK] Επιτυχής εξαγωγή {len(market_offers)} προϊόντων από {market_name}.")
                    else:
                        print(f"  [!] Δεν εξήχθησαν προϊόντα από {market_name}.")

                except Exception as ex:
                    print(f"  [X] Σφάλμα στο {market_name}: {ex}")
                    continue

            browser.close()
    except Exception as e:
        print(f"[X] Σφάλμα Playwright: {e}")

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
    json_file = scrape_all_supermarkets()
    upload_all_to_ftp()
