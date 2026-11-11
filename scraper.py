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
    
    # 1. Καθαρισμός από περιττά σύμβολα στην αρχή
    title = re.sub(r'^[\|\-\/\s]+', '', title)
    
    # 2. Διαγραφή άσχετων λέξεων/μηχανικών όρων
    artifacts = [
        "playlist_add", "favorite", "add", "remove", "Χρυσές Τιμές", 
        "Λίτ", "Τεμ", "τεμ", "τεμάχια", "κιλό", "κιλα", "γρ", "ml", "L", 
        "συσκ", "συσκευασία", "Νέο", "Προσωρινά μη διαθέσιμο", "Διαφήμιση", "Προσφορά"
    ]
    for art in artifacts:
        title = re.sub(rf'\b{art}\b', '', title, flags=re.IGNORECASE)
    
    # 3. Αφαίρεση μεμονωμένων αριθμών (όπως το 0) και περιττών συμβόλων στίξης
    title = re.sub(r'\b0\b', '', title)
    title = re.sub(r'[\/\|\-\.\,\s]+$', '', title)
    title = re.sub(r'\s*[\/\|\-]+\s*', ' ', title)
    
    return re.sub(r'\s+', ' ', title).strip()

def is_valid_product(title):
    blacklist = [
        "κατηγορίες", "συλλογές", "είσοδος", "emarket", "φίλτρα", 
        "λίστες", "αξία", "είδους", "εφαρμογή", "καταστήματα", "επικοινωνία"
    ]
    lower_title = title.lower()
    for word in blacklist:
        if word in lower_title:
            return False
    return len(title) > 4

def parse_products(raw_products, supermarket_name):
    parsed = []
    for item in raw_products:
        text = item["text"]
        img_url = item["image"]
        
        # Εντοπισμός τιμών
        prices = re.findall(r'(\d+[\.,]\d+\s*€)', text)
        
        # Καθαρισμός τίτλου από τιμές και περιττά σύμβολα
        title = text
        for price in prices:
            title = title.replace(price, "")
            
        title = clean_title(title)
        price_val = prices[-1] if prices else ""
        
        if len(title) > 4 and prices and price_val != "0,00 €" and img_url and img_url.startswith('http'):
            if is_valid_product(title):
                if not any(p['title'] == title and p['supermarket'] == supermarket_name for p in parsed):
                    parsed.append({
                        "title": title,
                        "price": price_val,
                        "all_prices": prices,
                        "image": img_url,
                        "supermarket": supermarket_name
                    })
    return parsed

# --- Στοχευμένη εξαγωγή για τον Σκλαβενίτη (μόνο τίτλοι προϊόντων) ---
def logic_sklavenitis(page, name, context=None):
    print("-> Στοχευμένη ανάγνωση προϊόντων Σκλαβενίτη...")
    
    try:
        page.wait_for_selector('article, div[class*="product"], div[class*="item"], div[class*="card"]', timeout=15000)
    except:
        print("-> Προειδοποίηση: Timeout στην αναμονή στοιχείων. Συνεχίζουμε με scroll...")

    for i in range(8):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)

    # Τραβάμε αποκλειστικά τα στοιχεία που περιέχουν τίτλο και τιμή, αποφεύγοντας τα γενικά μενού
    raw = page.evaluate("""() => {
        const results = [];
        // Αναζήτηση σε πιθανές κάρτες προϊόντων
        const cards = document.querySelectorAll('article, div[class*="product"], div[class*="item"], div[class*="card"]');
        
        cards.forEach(card => {
            const text = card.innerText;
            if (text && text.includes('€')) {
                // Προσπάθεια εύρεσης συγκεκριμένου τίτλου προϊόντος μέσα στην κάρτα
                const titleEl = card.querySelector('h2, h3, h4, a[class*="title"], span[class*="title"]');
                const cleanText = titleEl ? titleEl.innerText : text.split('\\n')[0];
                
                const img = card.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '') : '';
                
                if (imgSrc && imgSrc.startsWith('http') && cleanText.length > 3) {
                    // Συνδυάζουμε τον καθαρό τίτλο με την τιμή που υπάρχει στην κάρτα για να την αναγνωρίσει ο parser
                    const fullBlock = cleanText + ' ' + text;
                    if (!results.some(r => r.text === fullBlock)) {
                        results.push({ text: fullBlock, image: imgSrc });
                    }
                }
            }
        });
        return results;
    }""")
    
    print(f"-> Εντοπίστηκαν {len(raw)} καθαρά προϊόντα από τον Σκλαβενίτη.")
    return parse_products(raw, name)

def universal_scraper_logic(page, name):
    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)
        
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div, li, section');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 350 && text.length > 15) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '') : '';
                
                if (imgSrc && imgSrc.startsWith('http')) {
                    if (!results.some(r => r.text === cleanText)) {
                        results.push({ text: cleanText, image: imgSrc });
                    }
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def scrape_store(p, url, supermarket_name, logic_func):
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
        except Exception as nav_err:
            print(f"-> Προειδοποίηση πλοήγησης: {nav_err}")
            
        page.wait_for_timeout(5000)
        
        try:
            popup_ids = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), button:has-text('Συμφωνώ'), #onetrust-accept-btn-handler")
            if popup_ids.count() > 0:
                popup_ids.first().click()
                page.wait_for_timeout(2000)
        except:
            pass
            
        if supermarket_name == "Σκλαβενίτης":
            parsed = logic_func(page, supermarket_name, ctx)
        else:
            parsed = logic_func(page, supermarket_name)
            
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
            ("Σκλαβενίτης", "https://www.sklavenitis.gr/sylloges/prosfores/", logic_sklavenitis),
            ("ΑΒ Βασιλόπουλος", "https://www.ab.gr/search/promotions", universal_scraper_logic),
            ("Μασούτης", "https://www.masoutis.gr/offers", universal_scraper_logic),
            ("Κρητικός", "https://kritikos-sm.gr/offers/", universal_scraper_logic),
            ("Γαλαξίας", "https://galaxias.shop/eshop/2", universal_scraper_logic),
            ("My Market", "https://www.mymarket.gr/offers", universal_scraper_logic),
        ]
        
        for name, url, logic_func in targets:
            try:
                offers = scrape_store(p, url, name, logic_func)
                all_offers.extend(offers)
            except Exception as e:
                print(f"Σφάλμα εκτέλεσης για {name}:", e)

        unique_offers = []
        seen_titles = set()
        for offer in all_offers:
            key = (offer["supermarket"], offer["title"])
            if key not in seen_titles:
                seen_titles.add(key)
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
