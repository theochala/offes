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
    
    title = re.sub(r'\d+[\.,]\d+\s*€(?:/[^\s]+)?', '', title)
    title = re.sub(r'\d+\s*€(?:/[^\s]+)?', '', title)
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
        "φυλλάδια", "προσφορές", "λίστα αγορών", "είναι άδεια", "σύνολο", 
        "χρυσές τιμές", "mymarket.gr", "καλάθι", "no image",
        "φρούτα", "λαχανικά", "έτοιμες σαλάτες", "γαλακτοκομικά", "κρέατα", "ψάρια"
    ]
    lower_title = title.lower()
    for word in blacklist:
        if word in lower_title:
            if lower_title.strip() == word:
                return False
                
    if re.match(r'^[\d\s\.,€/+-]+$', title):
        return False
        
    return len(title) > 3

def parse_products(raw_products, supermarket_name):
    parsed = []
    for item in raw_products:
        text = item["text"]
        img_url = item["image"]
        
        # Πιο ευέλικτος εντοπισμός: πιάνει είτε απλή τιμή (π.χ. 2,59 €) είτε με μονάδα (π.χ. 3,00 €/τεμ. ή 60,00 €/λίτρο)
        all_matches = re.findall(r'(\d+[\.,]\d+\s*€(?:/[a-zA-Zα-ωΑ-Ω.]+)?)', text)
        
        prices = []
        for m in all_matches:
            num_part = m.split('€')[0].replace(',', '.').strip()
            try:
                val = float(num_part)
                if 0.05 <= val <= 60.0:
                    prices.append(m)
            except:
                pass

        if not prices:
            continue
            
        price_val = prices[-1]
        old_price = prices[0] if len(prices) > 1 and prices[0] != price_val else ""

        title = clean_title(item["title"])
        
        if len(title) > 3 and price_val and "0,00 €" not in price_val and img_url and img_url.startswith('http'):
            if is_valid_product(title):
                if not any(p['title'] == title and p['supermarket'] == supermarket_name for p in parsed):
                    parsed.append({
                        "title": title,
                        "price": price_val,
                        "old_price": old_price,
                        "all_prices": prices,
                        "image": img_url,
                        "supermarket": supermarket_name
                    })
    return parsed

def universal_scraper_logic(page, name):
    print(f"-> Σάρωση σελίδας για {name}...")
    
    for _ in range(5):
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)
        
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], div[class*="item"], div[class*="card"], li');
        
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 350 && text.length > 10) {
                const titleEl = el.querySelector('h2, h3, h4, a[class*="title"], span[class*="title"], .product-title, .title');
                let titleText = titleEl ? titleEl.innerText.trim() : '';
                
                if (!titleText || titleText.length < 3) {
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && !l.includes('€'));
                    titleText = lines.length > 0 ? lines[0] : '';
                }
                
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '') : '';
                
                if (imgSrc && imgSrc.startsWith('http') && titleText.length > 3) {
                    if (!results.some(r => r.title === titleText)) {
                        results.push({ title: titleText, text: text, image: imgSrc });
                    }
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def scrape_store(p, url, supermarket_name):
    print(f"\n--- Συλλογή από {supermarket_name} ---")
    browser = None
    try:
        launch_args = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1920,1080"
            ]
        }

        browser = p.chromium.launch(**launch_args)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="el-GR",
            timezone_id="Europe/Athens",
            extra_http_headers={
                "Accept-Language": "el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"'
            }
        )
        
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = ctx.new_page()
        print(f"-> Μετάβαση στη διεύθυνση: {url}")
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except:
            pass
            
        page.wait_for_timeout(5000)
        
        try:
            popup_ids = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), button:has-text('Συμφωνώ'), #onetrust-accept-btn-handler")
            if popup_ids.count() > 0:
                popup_ids.first().click()
                page.wait_for_timeout(2000)
        except:
            pass
            
        parsed = universal_scraper_logic(page, supermarket_name)
        browser.close()
        
        if parsed and len(parsed) > 0:
            print(f"-> Επιτυχία: {len(parsed)} προϊόντα από {supermarket_name}.")
            return parsed
        else:
            print(f"-> 0 προϊόντα βρέθηκαν για {supermarket_name}.")
            return []
            
    except Exception as e:
        print(f"-> Σφάλμα κατά τη συλλογή από {supermarket_name}: {e}")
        if browser:
            try:
                browser.close()
            except:
                pass
        return []

def upload_all_to_ftp():
    print("\n=== ΜΕΤΑΦΟΡΤΩΣΗ FTP ===")
    from ftplib import FTP
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("[!] Λείπουν τα FTP στοιχεία από τα GitHub Secrets.")
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
            ("Discount Markt", "https://discountmarkt.gr/offer-brochures/"),
        ]
        
        for name, url in targets:
            try:
                offers = scrape_store(p, url, name)
                all_offers.extend(offers)
            except Exception as e:
                print(f"Σφάλμα εκτέλεσης για {name}:", e)

        unique_offers = []
        seen_titles = set()
        for offer in all_offers:
            key_clean = (offer["supermarket"], offer["title"].lower().strip())
            if key_clean not in seen_titles:
                seen_titles.add(key_clean)
                unique_offers.append(offer)

        data = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_offers": len(unique_offers),
            "offers": unique_offers,
        }

        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"\nΣυνολική αποθήκευση {len(unique_offers)} μοναδικών προϊόντων στο clean_offers.json!")

    upload_all_to_ftp()
