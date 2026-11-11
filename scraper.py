from playwright.sync_api import sync_playwright
import json
import os
import re
import random
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

def random_delay(page, min_ms=1500, max_ms=3500):
    page.wait_for_timeout(random.randint(min_ms, max_ms))

def scrape_sklavenitis(page):
    print("Συλλογή από Σκλαβενίτη...")
    try:
        page.goto("https://www.sklavenitis.gr/fylladia/", timeout=60000, wait_until="domcontentloaded")
        random_delay(page, 4000, 6000)
    except Exception as e:
        print("Σφάλμα φόρτωσης Σκλαβενίτη:", e)
        return []
    
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1000)")
        random_delay(page, 1500, 2000)

    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, .product-item, div[class*="product"], div[class*="item"], div[class*="leaflet"]');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    parsed = parse_products(raw, "Σκλαβενίτης")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Σκλαβενίτη.")
    return parsed

def scrape_ab(page):
    print("Συλλογή από ΑΒ Βασιλόπουλο...")
    try:
        page.goto("https://www.ab.gr/search/promotions?page=0&size=30", timeout=60000, wait_until="domcontentloaded")
        random_delay(page, 4000, 6000)
    except Exception as e:
        print("Σφάλμα φόρτωσης σελίδας ΑΒ:", e)
        return []
    
    try:
        cookie_btn = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), #onetrust-accept-btn-handler")
        if cookie_btn.count() > 0:
            cookie_btn.first().click()
            random_delay(page, 1000, 2000)
    except:
        pass

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        random_delay(page, 2000, 2500)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, product-card-view, div[class*="product"], div[class*="item"], div[class*="promotion"]');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 300 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    parsed = parse_products(raw, "ΑΒ Βασιλόπουλος")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από ΑΒ.")
    return parsed

def scrape_masoutis(page):
    print("Συλλογή από Μασούτη...")
    try:
        page.goto("https://www.masoutis.gr/fylladia", timeout=60000, wait_until="domcontentloaded")
        random_delay(page, 4000, 6000)
    except Exception as e:
        print("Σφάλμα φόρτωσης Μασούτη:", e)
        return []

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        random_delay(page, 1500, 2000)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], .item, div[class*="card"], div[class*="leaflet"]');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    parsed = parse_products(raw, "Μασούτης")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Μασούτη.")
    return parsed

def scrape_kritikos(page):
    print("Συλλογή από Κρητικό...")
    try:
        page.goto("https://kritikos-sm.gr/offers/", timeout=60000, wait_until="domcontentloaded")
        random_delay(page, 3000, 5000)
    except:
        return []

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        random_delay(page, 1500, 2500)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"]');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    parsed = parse_products(raw, "Κρητικός")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Κρητικό.")
    return parsed

def scrape_galaxias(page):
    print("Συλλογή από Γαλαξία...")
    try:
        page.goto("https://galaxias.shop/eshop/2", timeout=60000, wait_until="domcontentloaded")
        random_delay(page, 4000, 6000)
    except:
        return []

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        random_delay(page, 2000, 2500)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], .product-card');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!cleanText.includes('Κατηγορίες') && !results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    parsed = parse_products(raw, "Γαλαξίας")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Γαλαξία.")
    return parsed

def scrape_mymarket(page):
    print("Συλλογή από My Market...")
    try:
        page.goto("https://www.mymarket.gr/offers", timeout=60000, wait_until="domcontentloaded")
        random_delay(page, 4000, 6000)
    except Exception as e:
        print("Σφάλμα φόρτωσης My Market:", e)
        return []

    try:
        cookie_btn = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), #onetrust-accept-btn-handler")
        if cookie_btn.count() > 0:
            cookie_btn.first().click()
            random_delay(page, 1000, 2000)
    except:
        pass

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        random_delay(page, 2000, 2500)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], .item');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    parsed = parse_products(raw, "My Market")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από My Market.")
    return parsed

def scrape_discountmarket(page):
    print("Συλλογή από Discount Market...")
    try:
        page.goto("https://www.discountmarket.gr/", timeout=60000, wait_until="domcontentloaded")
        random_delay(page, 4000, 6000)
    except Exception as e:
        print("Σφάλμα φόρτωσης Discount Market:", e)
        return []

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        random_delay(page, 1500, 2500)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], .product-item, div[class*="item"]');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 250 && text.length > 10) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    parsed = parse_products(raw, "Discount Market")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Discount Market.")
    return parsed

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

    ftp = None
    try:
        ftp = FTP(ftp_server, timeout=30)
        ftp.login(user=ftp_user, passwd=ftp_pass)

        ftp.cwd("prosfores.infy.click")
        ftp.cwd("htdocs")

        with OUTPUT_FILE.open("rb") as file:
            ftp.storbinary("STOR clean_offers.json", file)
        
        print("[OK] Το clean_offers.json ανέβηκε επιτυχώς στο /prosfores.infy.click/htdocs!")
        ftp.quit()
    except Exception as error:
        print(f"[X] Σφάλμα FTP: {error}")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="el-GR",
            timezone_id="Europe/Athens"
        )
        
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        context.add_init_script("window.navigator.chrome = { runtime: {} };")
        
        page = context.new_page()
        all_offers = []
        
        scrapers = [
            scrape_sklavenitis, 
            scrape_ab, 
            scrape_masoutis, 
            scrape_kritikos, 
            scrape_galaxias, 
            scrape_mymarket,
            scrape_discountmarket
        ]
        
        for scraper_func in scrapers:
            try:
                all_offers.extend(scraper_func(page))
            except Exception as e:
                print("Σφάλμα:", e)

        browser.close()
        
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
