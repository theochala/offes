from playwright.sync_api import sync_playwright
import json
import os
import re
from datetime import datetime
from pathlib import Path

OUTPUT_FILE = Path("clean_offers.json")

def clean_title(title):
    if not title:
        return ""
    title = re.sub(r'\d+[\.,]\d+\s*€', '', title)
    title = re.sub(r'\d+\s*€', '', title)
    title = re.sub(r'^[\|\-\/\s]+', '', title)
    title = re.sub(r'[\/\|\-\.\,\s]+$', '', title)
    title = re.sub(r'\s*[\/\|\-]+\s*', ' ', title)
    return re.sub(r'\s+', ' ', title).strip()

def is_valid_product(title):
    if not title:
        return False
    
    blacklist = [
        "κατηγορίες", "συλλογές", "είσοδος", "emarket", "φίλτρα", 
        "λίστες", "αξία", "είδους", "εφαρμογή", "καταστήματα", "επικοινωνία",
        "φυλλάδια", "περισσότερα", "εβδομάδα", "αρχική", "αγόρασε", "καλάθι",
        "διαφήμιση", "δώρο", "προσφορά", "νέο", "προσθήκη", "κιλό", "τεμάχιο"
    ]
    
    lower_title = title.lower().strip()
    if lower_title in blacklist or any(lower_title.startswith(w) for w in ["προσθήκη", "διαφήμιση", "δώρο"]):
        return False
        
    if re.match(r'^[\d\s\.,€+-]+$', title):
        return False
        
    return len(title) > 3

def scrape_generic_store(page, name, card_selector, title_selector, price_selector, img_selector):
    print(f"-> Στοχευμένη σάρωση για {name}...")
    
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1500)")
        page.wait_for_timeout(2000)

    # Μεταφορά των selectors με ασφάλεια ως όρισμα στη JS (αποφυγή SyntaxError)
    selectors = {
        "card": card_selector,
        "title": title_selector,
        "price": price_selector,
        "img": img_selector
    }

    products_data = page.evaluate("""(sel) => {
        const results = [];
        const cards = document.querySelectorAll(sel.card);
        
        cards.forEach(card => {
            const titleEl = card.querySelector(sel.title);
            const priceEl = card.querySelector(sel.price);
            const imgEl = card.querySelector(sel.img);
            
            const title = titleEl ? titleEl.innerText.trim() : '';
            const priceText = priceEl ? priceEl.innerText.trim() : '';
            let imgSrc = imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || imgEl.getAttribute('data-lazy-src') || '') : '';
            
            if (title && priceText && imgSrc) {
                results.push({
                    title: title,
                    priceText: priceText,
                    image: imgSrc.split(' ')[0]
                });
            }
        });
        return results;
    }""", selectors)

    parsed = []
    for item in products_data:
        title = clean_title(item["title"])
        prices = re.findall(r'(\d+[\.,]\d+\s*€)', item["priceText"])
        if not prices:
            prices = re.findall(r'(\d+[\.,]\d+)', item["priceText"])
            prices = [p + " €" for p in prices]
            
        price_val = prices[-1] if prices else ""
        
        if is_valid_product(title) and price_val and item["image"].startswith('http'):
            if not any(p['title'] == title and p['supermarket'] == name for p in parsed):
                parsed.append({
                    "title": title,
                    "price": price_val,
                    "all_prices": prices,
                    "image": item["image"],
                    "supermarket": name
                })
                
    return parsed

def scrape_store(p, url, name):
    print(f"\n--- Συλλογή από {name} ---")
    browser = None
    try:
        launch_args = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1920,1080"
            ]
        }
        browser = p.chromium.launch(**launch_args)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="el-GR"
        )
        page = ctx.new_page()
        print(f"-> Μετάβαση στη διεύθυνση: {url}")
        
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        
        try:
            popup = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), #onetrust-accept-btn-handler")
            if popup.count() > 0:
                popup.first().click()
                page.wait_for_timeout(2000)
        except:
            pass

        if name == "Σκλαβενίτης":
            parsed = scrape_generic_store(page, name, "article, div.product-item, div[class*='product']", "h3, h2, a[class*='title'], [class*='Title']", "[class*='price'], [class*='Price']", "img")
        elif name == "ΑΒ Βασιλόπουλος":
            parsed = scrape_generic_store(page, name, "article, div[class*='product-card']", "h3, h2, [class*='title']", "[class*='price']", "img")
        elif name == "Μασούτης":
            parsed = scrape_generic_store(page, name, "div[class*='product'], article", "h3, h2, [class*='title']", "[class*='price']", "img")
        elif name == "Κρητικός":
            parsed = scrape_generic_store(page, name, "div[class*='product'], article, li", "h3, h2, [class*='title']", "[class*='price']", "img")
        elif name == "Γαλαξίας":
            parsed = scrape_generic_store(page, name, "div[class*='product'], article, li", "h3, h2, [class*='title']", "[class*='price']", "img")
        elif name == "My Market":
            parsed = scrape_generic_store(page, name, "div[class*='product'], article", "h3, h2, [class*='title']", "[class*='price']", "img")
        else:
            parsed = scrape_generic_store(page, name, "article, div, li", "h2, h3, h4", "[class*='price']", "img")

        browser.close()
        
        if parsed:
            print(f"-> Επιτυχία: {len(parsed)} προϊόντα από {name}.")
            return parsed
        print(f"-> 0 προϊόντα βρέθηκαν για {name}.")
        return []
    except Exception as e:
        print(f"-> Σφάλμα για {name}: {e}")
        if browser:
            try: browser.close()
            except: pass
        return []

def upload_all_to_ftp():
    print("\n=== ΜΕΤΑΦΟΡΤΩΣΗ FTP ===")
    from ftplib import FTP
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("[!] Λείπουν τα FTP credentials.")
        return

    if not OUTPUT_FILE.exists():
        print("[!] Δεν βρέθηκε το clean_offers.json.")
        return

    try:
        ftp = FTP(ftp_server, timeout=30)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        ftp.cwd("prosfores.infy.click")
        ftp.cwd("htdocs")

        with OUTPUT_FILE.open("rb") as file:
            ftp.storbinary("STOR clean_offers.json", file)
        print("[OK] Το clean_offers.json ανέβηκε επιτυχώς στο FTP!")
        ftp.quit()
    except Exception as error:
        print(f"[X] Σφάλμα FTP: {error}")

if __name__ == "__main__":
    with sync_playwright() as p:
        all_offers = []
        targets = [
            ("Σκλαβενίτης", "https://www.sklavenitis.gr/sylloges/prosfores/"),
            ("ΑΒ Βασιλόπουλος", "https://www.ab.gr/search/promotions"),
            ("Μασούτης", "https://www.masoutis.gr/offers"),
            ("Κρητικός", "https://kritikos-sm.gr/offers/"),
            ("Γαλαξίας", "https://galaxias.shop/eshop/2"),
            ("My Market", "https://www.mymarket.gr/offers"),
        ]
        
        for name, url in targets:
            try:
                all_offers.extend(scrape_store(p, url, name))
            except Exception as e:
                print(f"Σφάλμα {name}: {e}")

        unique_offers = []
        seen = set()
        for offer in all_offers:
            key = (offer["supermarket"], offer["title"].lower().strip())
            if key not in seen:
                seen.add(key)
                unique_offers.append(offer)

        data = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_offers": len(unique_offers),
            "offers": unique_offers,
        }

        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"\nΣυνολική αποθήκευση {len(unique_offers)} καθαρών προϊόντων!")

    upload_all_to_ftp()
