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
    print("=== [1/3] Εκκίνηση Πλήρους Scraper ===")
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
                    
                    # Πολλαπλό scroll για να φορτώσουν όλα τα δυναμικά προϊόντα (Lazy Loading)
                    for _ in range(3):
                        page.mouse.wheel(0, 1500)
                        page.wait_for_timeout(1500)

                    market_offers = []

                    # Γενικοί και ειδικοί selectors για να πιάσουμε κάθε πιθανή κάρτα προϊόντος
                    cards = page.locator("article, div[class*='product'], div[class*='Card'], div[class*='item'], li[class*='product']").all()

                    print(f"  [i] Εντοπίστηκαν {len(cards)} υποψήφια στοιχεία στο {market_name}.")

                    for card in cards[:30]:
                        try:
                            title_el = None
                            price_el = None
                            old_price_el = None
                            img_src = ""

                            # Αναζήτηση τίτλου με πολλαπλάσια κριτήρια
                            for t_sel in ["h2", "h3", "h4", ".product-title", ".title", "a[title]", "[class*='title']", "[class*='name']"]:
                                el = card.locator(t_sel).first
                                if el.count() > 0:
                                    txt = el.inner_text().strip()
                                    if len(txt) > 3 and not any(w in txt.lower() for w in ["καλάθι", "σούπερ", "αρχική"]):
                                        title_el = txt
                                        break

                            # Αναζήτηση τιμής με πολλαπλάσια κριτήρια
                            for p_sel in [".price", ".current-price", ".value", "[class*='price']", "[class*='amount']", "span"]:
                                el = card.locator(p_sel).first
                                if el.count() > 0:
                                    txt = el.inner_text().strip()
                                    if any(char.isdigit() for char in txt) and ('€' in txt or len(txt) < 8):
                                        price_el = txt
                                        break

                            # Αναζήτηση παλιάς τιμής
                            for op_sel in [".old-price", ".original-price", "del", "[class*='old']"]:
                                el = card.locator(op_sel).first
                                if el.count() > 0:
                                    old_price_el = el.inner_text().strip()
                                    break

                            # Εικόνα προϊόντος
                            img_el = card.locator("img").first
                            if img_el.count() > 0:
                                src = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                                if src and src.startswith("http"):
                                    img_src = src

                            if title_el and price_el:
                                # Αποφυγή διπλοεγγραφών
                                if not any(o['title'] == title_el for o in market_offers):
                                    market_offers.append({
                                        "supermarket": market_name,
                                        "title": title_el,
                                        "price": price_el,
                                        "old_price": old_price_el or "",
                                        "image": img_src if img_src else "https://via.placeholder.com/150?text=Offer",
                                        "date": datetime.now().strftime("%Y-%m-%d")
                                    })
                        except:
                            continue

                    if market_offers:
                        all_offers.extend(market_offers)
                        print(f"  [OK] Επιτυχής εξαγωγή {len(market_offers)} προϊόντων από {market_name}.")
                    else:
                        print(f"  [!] Δεν βρέθηκαν έγκυρα προϊόντα στο {market_name}.")

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
