from playwright.sync_api import sync_playwright
import json
import os
import re
from datetime import datetime
from pathlib import Path

OUTPUT_FILE = Path("clean_offers.json")

def clean_title(title):
    artifacts = [
        "playlist_add", "favorite", "add", "remove", "Χρυσές Τιμές", 
        "Λίτ", "Τεμ", "/", "Νέο", "Προσωρινά μη διαθέσιμο", "Διαφήμιση"
    ]
    for art in artifacts:
        title = title.replace(art, "")
    
    words = title.split()
    seen = []
    for w in words:
        if w not in seen or len(w) > 4:
            seen.append(w)
    
    title = " ".join(seen)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def parse_products(raw_products, supermarket_name):
    parsed = []
    for item in raw_products:
        text = item["text"]
        img_url = item["image"]
        
        prices = re.findall(r'(\d+[\.,]\d+\s*€)', text)
        title = text
        for price in prices:
            title = title.replace(price, "")
            
        title = clean_title(title)
        price_val = prices[-1] if prices else ""
        
        if len(title) > 5 and prices and price_val != "0,00 €" and img_url and img_url.startswith('http'):
            if not any(p['title'] == title and p['supermarket'] == supermarket_name for p in parsed):
                parsed.append({
                    "title": title,
                    "price": price_val,
                    "all_prices": prices,
                    "image": img_url,
                    "supermarket": supermarket_name
                })
    return parsed

def scrape_store(p, url, scraper_logic, supermarket_name):
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
                "--disable-blink-features=AutomationControlled"
            ]
        }

        browser = p.chromium.launch(**launch_args)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="el-GR",
            timezone_id="Europe/Athens"
        )
        
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        context.add_init_script("window.navigator.chrome = { runtime: {} };")
        
        page = context.new_page()
        
        print(f"-> Μετάβαση στη διεύθυνση: {url}")
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        
        parsed = scraper_logic(page, supermarket_name)
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

# --- Λογική εξαγωγής ανά κατάστημα ---

def logic_sklavenitis(page, name):
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    raw = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('article, .product-item, div[class*="product"], div[class*="item"]').forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) results.push({ text: cleanText, image: imgSrc });
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def logic_ab(page, name):
    try:
        cookie_btn = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), #onetrust-accept-btn-handler")
        if cookie_btn.count() > 0:
            cookie_btn.first().click()
            page.wait_for_timeout(1500)
    except:
        pass
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    raw = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('article, product-card-view, div[class*="product"], div[class*="item"]').forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 300 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) results.push({ text: cleanText, image: imgSrc });
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def logic_masoutis(page, name):
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    raw = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('article, div[class*="product"], .item').forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) results.push({ text: cleanText, image: imgSrc });
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def logic_kritikos(page, name):
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(1500)
    raw = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('article, div[class*="product"]').forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) results.push({ text: cleanText, image: imgSrc });
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def logic_galaxias(page, name):
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    raw = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('article, div[class*="product"], .product-card').forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!cleanText.includes('Κατηγορίες') && !results.some(r => r.text === cleanText)) results.push({ text: cleanText, image: imgSrc });
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

def logic_mymarket(page, name):
    try:
        cookie_btn = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), #onetrust-accept-btn-handler")
        if cookie_btn.count() > 0:
            cookie_btn.first().click()
            page.wait_for_timeout(1000)
    except:
        pass
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(1500)
    raw = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('article, div[class*="product"], .item').forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) results.push({ text: cleanText, image: imgSrc });
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

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
            ("ΑΒ Βασιλόπουλος", "https://www.ab.gr/search/promotions", logic_ab),
            ("Μασούτης", "https://www.masoutis.gr/offers", logic_masoutis),
            ("Κρητικός", "https://kritikos-sm.gr/offers/", logic_kritikos),
            ("Γαλαξίας", "https://galaxias.shop/eshop/2", logic_galaxias),
            ("My Market", "https://www.mymarket.gr/offers", logic_mymarket),
        ]
        
        for name, url, logic_func in targets:
            try:
                offers = scrape_store(p, url, logic_func, name)
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
