from playwright.sync_api import sync_playwright
import json
import re
import os
import requests
from requests.auth import HTTPBasicAuth
import ftplib

def clean_title(title):
    artifacts = [
        "playlist_add", "favorite", "add", "remove", "Χρυσές Τιμές", 
        "Λίτ", "Τεμ", "/", "Νέο", "Προσωρινά μη διαθέσιμο", "Διαφήμιση", "με Lidl Plus", "Χωρίς Lidl Plus"
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

def scrape_sklavenitis(page):
    print("Συλλογή από Σκλαβενίτη...")
    page.goto("https://www.sklavenitis.gr/sylloges/prosfores/")
    page.wait_for_timeout(6000)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, .product-item, div[class*="product"]');
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
    page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    try:
        page.goto("https://www.ab.gr/search/promotions", timeout=60000)
        page.wait_for_timeout(6000)
    except Exception as e:
        print("Σφάλμα φόρτωσης σελίδας ΑΒ:", e)
        return []
    
    try:
        cookie_btn = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), #onetrust-accept-btn-handler")
        if cookie_btn.count() > 0:
            cookie_btn.first().click()
            page.wait_for_timeout(2000)
    except:
        pass

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, product-card-view, div[class*="product"]');
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
    page.goto("https://www.masoutis.gr/offers")
    page.wait_for_timeout(5000)
    
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
    parsed = parse_products(raw, "Μασούτης")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Μασούτη.")
    return parsed

def scrape_kritikos(page):
    print("Συλλογή από Κρητικό...")
    try:
        page.goto("https://kritikos-sm.gr/offers/?srsltid=AYCX9vJWXPLOaa4mCSyC7xt-dwrv1ovQ7pkBaLPHp-8tjTfpPrQCT6pA", timeout=60000)
        page.wait_for_timeout(5000)
    except:
        return []

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    
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
        page.goto("https://galaxias.shop/eshop/2?promos=isExtraBonus&promos=isBravoBonus&promos=isKalathiNoikokiriou&promos=isSumferei&promos=isTileoptiko&promos=isGoldPrices", timeout=60000)
        page.wait_for_timeout(6000)
    except:
        return []

    for _ in range(5):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    
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
        page.wait_for_timeout(6000)
    except Exception as e:
        print("Σφάλμα φόρτωσης My Market:", e)
        return []

    try:
        cookie_btn = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), #onetrust-accept-btn-handler")
        if cookie_btn.count() > 0:
            cookie_btn.first().click()
            page.wait_for_timeout(2000)
    except:
        pass

    for _ in range(5):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    
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

def scrape_lidl(page):
    print("Συλλογή από Lidl...")
    try:
        page.goto("https://www.lidl-hellas.gr/c/fagito-poto/s10068374", timeout=60000)
        page.wait_for_timeout(7000)
    except Exception as e:
        print("Σφάλμα φόρτωσης Lidl:", e)
        return []

    try:
        cookie_btn = page.locator("button:has-text('Αποδοχή'), button:has-text('Accept'), #onetrust-accept-btn-handler")
        if cookie_btn.count() > 0:
            cookie_btn.first().click()
            page.wait_for_timeout(2000)
    except:
        pass

    for _ in range(6):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
    
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('.ret-o-card, div[class*="product"], div[class*="Grid"], article, li.ret-m-product-grid__item');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 350 && text.length > 5) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                const imgSrc = img ? (img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '') : '';
                if (!results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    parsed = parse_products(raw, "Lidl")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Lidl.")
    return parsed

def upload_to_wordpress(json_file="clean_offers.json"):
    if not os.path.exists(json_file):
        print("Το αρχείο clean_offers.json δεν βρέθηκε.")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        offers = json.load(f)

    wp_url = os.getenv("WP_URL", "https://prosfores.infy.click")
    wp_user = os.getenv("WP_USER")
    wp_pass = os.getenv("WP_APP_PASSWORD")

    if not wp_user or not wp_pass:
        print("Δεν βρέθηκαν τα credentials του WordPress στα GitHub Secrets. Παράλειψη ανέβασματος.")
        return

    api_url = f"{wp_url}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(wp_user, wp_pass)

    print(f"\nΞεκινάει το ανέβασμα {len(offers)} προσφορών στο WordPress...")

    for offer in offers:
        title = f"[{offer['supermarket']}] {offer['title']}"
        content = f"""
        <p><strong>Σούπερ Μάρκετ:</strong> {offer['supermarket']}</p>
        <p><strong>Τιμή:</strong> <span style="color: #d9534f; font-size: 1.3em; font-weight: bold;">{offer['price']}</span></p>
        <p><img src="{offer['image']}" alt="{offer['title']}" style="max-width:300px; height:auto; border-radius: 8px;"/></p>
        """
        
        post_data = {
            "title": title,
            "content": content,
            "status": "publish"
        }

        try:
            response = requests.post(api_url, json=post_data, auth=auth, timeout=30)
            if response.status_code == 201:
                print(f"✔ Δημοσιεύτηκε: {title}")
            else:
                print(f"✖ Σφάλμα ({response.status_code}): {response.text[:100]}")
        except Exception as e:
            print(f"✖ Εξαίρεση κατά το ανέβασμα: {e}")

def upload_to_ftp():
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not ftp_server or not ftp_user or not ftp_pass:
        print("Δεν βρέθηκαν τα FTP credentials στα GitHub Secrets. Παράλειψη μεταφόρτωσης FTP.")
        return

    print("\nΣύνδεση στο FTP του InfinityFree...")
    try:
        with ftplib.FTP(ftp_server, ftp_user, ftp_pass) as ftp:
            ftp.cwd("/htdocs/")
            with open("clean_offers.json", "rb") as f:
                ftp.storbinary("STOR clean_offers.json", f)
            print("✔ Το αρχείο clean_offers.json ανέβηκε επιτυχώς μέσω FTP!")
    except Exception as e:
        print(f"✖ Σφάλμα κατά το FTP upload: {e}")

# Εκτέλεση Scraping
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    all_offers = []
    scrapers = [scrape_sklavenitis, scrape_ab, scrape_masoutis, scrape_kritikos, scrape_galaxias, scrape_mymarket, scrape_lidl]
    
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

    with open("clean_offers.json", "w", encoding="utf-8") as f:
        json.dump(unique_offers, f, ensure_ascii=False, indent=4)
        print(f"\nΑποθήκευση {len(unique_offers)} μοναδικών προσφορών στο clean_offers.json!")

# Αυτόματη αποστολή
upload_to_wordpress()
upload_to_ftp()
