from playwright.sync_api import sync_playwright
import json
import os
import re
from datetime import datetime
from pathlib import Path
from ftplib import FTP

OUTPUT_FILE = Path("clean_offers.json")

# --- ΒΑΛΕ ΕΔΩ ΤΑ ΣΤΟΙΧΕΙΑ ΤΟΥ FTP ΣΟΥ ---
FTP_SERVER = "ftpupload.net"  # Ή ο διακομιστής FTP του InfinityFree
FTP_USER = "if0_xxxxxxx"        # Το Username σου από το InfinityFree
FTP_PASS = "το_password_σου"    # Το Password σου

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

def parse_products(raw_products, supermarket_name):
    parsed = []
    for item in raw_products:
        text = item["text"]
        img_url = item["image"]
        
        prices = re.findall(r'(\d+[\.,]\d+\s*€)', text)
        if not prices:
            prices = re.findall(r'(\d+[\.,]\d+)', text)
            prices = [p + " €" for p in prices]
            
        title = clean_title(item["title"])
        price_val = prices[-1] if prices else ""
        
        if len(title) > 3 and prices and price_val != "0,00 €" and img_url and img_url.startswith('http'):
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

def logic_sklavenitis(page, name):
    print(f"-> Σάρωση σελίδας για {name}...")
    for _ in range(8):
        page.evaluate("window.scrollBy(0, 1500)")
        page.wait_for_timeout(2000)
        
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div, li, section');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 400 && text.length > 10) {
                const titleEl = el.querySelector('h2, h3, h4, [class*="title"], [class*="Heading"]');
                let titleText = titleEl ? titleEl.innerText.trim() : '';
                
                if (!titleText || titleText.toLowerCase().includes('προσθήκη') || titleText.toLowerCase() === 'κιλό' || titleText.toLowerCase() === 'διαφήμιση' || titleText.toLowerCase() === 'δώρο') {
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && !l.includes('€') && !l.toLowerCase().includes('προσθήκη') && l.toLowerCase() !== 'κιλό' && l.toLowerCase() !== 'διαφήμιση' && l.toLowerCase() !== 'δώρο');
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

def logic_ab(page, name):
    print(f"-> Στοχευμένη ανάγνωση για {name}...")
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        pass
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1500)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('article, div[class*="product"], div[class*="grid"], div[class*="card"], li');
        cards.forEach(card => {
            const text = card.innerText;
            if (text && text.includes('€')) {
                const titleEl = card.querySelector('h2, h3, h4, [class*="title"], [class*="Heading"]');
                let productTitle = titleEl ? titleEl.innerText.trim() : '';
                if (!productTitle || productTitle.toLowerCase().includes('προσθήκη')) {
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && !l.includes('€'));
                    productTitle = lines.length > 0 ? lines[0] : '';
                }
                const img = card.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (imgSrc && imgSrc.startsWith('http') && productTitle.length > 3) {
                    if (!results.some(r => r.title === productTitle)) {
                        results.push({ title: productTitle, text: text, image: imgSrc.split(' ')[0] });
                    }
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def universal_scraper_logic(page, name):
    print(f"-> Ευέλικτη σάρωση για {name}...")
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1500)")
        page.wait_for_timeout(2000)
        
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], div[class*="card"], li, section');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 500 && text.length > 10) {
                const titleEl = el.querySelector('h2, h3, h4, [class*="title"], [class*="Heading"], a');
                let titleText = titleEl ? titleEl.innerText.trim() : '';
                
                if (!titleText || titleText.toLowerCase().includes('προσθήκη') || titleText.toLowerCase() === 'διαφήμιση' || titleText.toLowerCase() === 'δώρο') {
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && !l.includes('€') && !l.toLowerCase().includes('προσθήκη') && l.toLowerCase() !== 'διαφήμιση' && l.toLowerCase() !== 'δώρο');
                    titleText = lines.length > 0 ? lines[0] : '';
                }
                
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '') : '';
                
                if (imgSrc && imgSrc.startsWith('http') && titleText.length > 3) {
                    if (!results.some(r => r.title === titleText)) {
                        results.push({ title: titleText, text: text, image: imgSrc.split(' ')[0] });
                    }
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def scrape_store(p, url, name, logic_func=None):
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

        if logic_func:
            parsed = logic_func(page, name)
        else:
            parsed = universal_scraper_logic(page, name)

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
    if not all([FTP_SERVER, FTP_USER, FTP_PASS]) or "xxxxxxx" in FTP_USER:
        print("[!] Παρακαλώ συμπληρώστε τα στοιχεία FTP μέσα στο scraper.py!")
        return

    if not OUTPUT_FILE.exists():
        print("[!] Δεν βρέθηκε το clean_offers.json.")
        return

    try:
        ftp = FTP(FTP_SERVER, timeout=30)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
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
            ("ΑΒ Βασιλόπουλος", "https://www.ab.gr/search/promotions", logic_ab),
            ("Μασούτης", "https://www.masoutis.gr/offers", None),
            ("Κρητικός", "https://kritikos-sm.gr/offers/", None),
            ("Γαλαξίας", "https://galaxias.shop/eshop/2", None),
            ("My Market", "https://www.mymarket.gr/offers", None),
        ]
        
        for name, url, logic_func in targets:
            try:
                all_offers.extend(scrape_store(p, url, name, logic_func))
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
