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
    blacklist = [
        "κατηγορίες", "συλλογές", "είσοδος", "emarket", "φίλτρα", 
        "λίστες", "αξία", "είδους", "εφαρμογή", "καταστήματα", "επικοινωνία", "φυλλάδια", "προσφορές"
    ]
    lower_title = title.lower()
    for word in blacklist:
        if word in lower_title:
            return False
    return len(title) > 3

def parse_products(raw_products, supermarket_name):
    parsed = []
    for item in raw_products:
        text = item["text"]
        img_url = item["image"]
        prices = re.findall(r'(\d+[\.,]\d+\s*€)', text)
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

# --- 1. Σκλαβενίτης ---
def logic_sklavenitis(page, name):
    print("-> Στοχευμένη ανάγνωση Σκλαβενίτη...")
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('article, div[class*="product"], div[class*="item"], div[class*="card"]');
        cards.forEach(card => {
            const text = card.innerText;
            if (text && text.includes('€')) {
                const titleEl = card.querySelector('h2, h3, h4, a[class*="title"], span[class*="title"]');
                const productTitle = titleEl ? titleEl.innerText.trim() : '';
                const img = card.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (imgSrc && imgSrc.startsWith('http') && productTitle.length > 2) {
                    results.push({ title: productTitle, text: text, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

# --- 2. ΑΒ Βασιλόπουλος ---
def logic_ab(page, name):
    print("-> Στοχευμένη ανάγνωση ΑΒ Βασιλόπουλος...")
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('article, div[class*="product"], product-card, div[data-testid*="product"]');
        if (cards.length === 0) {
            // Fallback γενική αναζήτηση αν δεν βρεθούν τα συγκεκριμένα tags
            const allDivs = document.querySelectorAll('div');
            allDivs.forEach(div => {
                const text = div.innerText;
                if (text && text.includes('€') && text.length < 250) {
                    const img = div.querySelector('img');
                    const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                    if (imgSrc && imgSrc.startsWith('http')) {
                        results.push({ title: text.split('\\n')[0], text: text, image: imgSrc });
                    }
                }
            });
        }
        return results;
    }""")
    return parse_products(raw, name)

# --- 3. Μασούτης ---
def logic_masoutis(page, name):
    print("-> Στοχευμένη ανάγνωση Μασούτης...")
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('.product-item, div[class*="product"], article, li');
        cards.forEach(card => {
            const text = card.innerText;
            if (text && text.includes('€')) {
                const titleEl = card.querySelector('h2, h3, a, .title');
                const productTitle = titleEl ? titleEl.innerText.trim() : text.split('\\n')[0];
                const img = card.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (imgSrc && imgSrc.startsWith('http') && productTitle.length > 2) {
                    results.push({ title: productTitle, text: text, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

# --- 4. Κρητικός ---
def logic_kritikos(page, name):
    print("-> Στοχευμένη ανάγνωση Κρητικός...")
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('.product, div[class*="product"], article, .col');
        cards.forEach(card => {
            const text = card.innerText;
            if (text && text.includes('€')) {
                const titleEl = card.querySelector('h2, h3, h4, a, span[class*="title"]');
                const productTitle = titleEl ? titleEl.innerText.trim() : text.split('\\n')[0];
                const img = card.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (imgSrc && imgSrc.startsWith('http') && productTitle.length > 2) {
                    results.push({ title: productTitle, text: text, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

# --- 5. Γαλαξίας ---
def logic_galaxias(page, name):
    print("-> Στοχευμένη ανάγνωση Γαλαξίας...")
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('div[class*="product"], article, li, .item');
        cards.forEach(card => {
            const text = card.innerText;
            if (text && text.includes('€')) {
                const titleEl = card.querySelector('h2, h3, a, .title');
                const productTitle = titleEl ? titleEl.innerText.trim() : text.split('\\n')[0];
                const img = card.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (imgSrc && imgSrc.startsWith('http') && productTitle.length > 2) {
                    results.push({ title: productTitle, text: text, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

# --- 6. My Market ---
def logic_mymarket(page, name):
    print("-> Στοχευμένη ανάγνωση My Market...")
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('article, div[class*="product"], div[class*="item"]');
        cards.forEach(card => {
            const text = card.innerText;
            if (text && text.includes('€')) {
                const titleEl = card.querySelector('h2, h3, a, span[class*="title"]');
                const productTitle = titleEl ? titleEl.innerText.trim() : text.split('\\n')[0];
                const img = card.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (imgSrc && imgSrc.startsWith('http') && productTitle.length > 2) {
                    results.push({ title: productTitle, text: text, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    return parse_products(raw, name)

# --- 7. Discount Markt ---
def logic_discountmarkt(page, name):
    print("-> Στοχευμένη ανάγνωση Discount Markt...")
    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('div[class*="product"], article, div[class*="brochure"], div[class*="item"], li');
        cards.forEach(card => {
            const text = card.innerText;
            if (text && text.includes('€')) {
                const titleEl = card.querySelector('h2, h3, h4, a, span, p');
                const productTitle = titleEl ? titleEl.innerText.trim() : text.split('\\n')[0];
                const img = card.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || '') : '';
                if (imgSrc && imgSrc.startsWith('http') && productTitle.length > 2) {
                    results.push({ title: productTitle, text: text, image: imgSrc });
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
            ("ΑΒ Βασιλόπουλος", "https://www.ab.gr/search/promotions", logic_ab),
            ("Μασούτης", "https://www.masoutis.gr/offers", logic_masoutis),
            ("Κρητικός", "https://kritikos-sm.gr/offers/", logic_kritikos),
            ("Γαλαξίας", "https://galaxias.shop/eshop/2", logic_galaxias),
            ("My Market", "https://www.mymarket.gr/offers", logic_mymarket),
            ("Discount Markt", "https://discountmarkt.gr/offer-brochures/", logic_discountmarkt),
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
