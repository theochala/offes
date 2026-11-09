import json
import re
import requests
from bs4cript import BeautifulSoup # ή BeautifulSoup από bs4
from playwright.sync_api import sync_playwright

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

# 1. Κρητικός (με Playwright αφού δουλεύει άψογα)
def scrape_kritikos(p):
    print("Συλλογή από Κρητικό...")
    try:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://kritikos-sm.gr/offers/", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(4):
            page.evaluate("window.scrollBy(0, 1000)")
            page.wait_for_timeout(2000)
        
        raw = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('article, div[class*="product"]').forEach(el => {
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
        browser.close()
        parsed = parse_products(raw, "Κρητικός")
        print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Κρητικό.")
        return parsed
    except Exception as e:
        print(f"Σφάλμα Κρητικός: {e}")
        return []

# 2. Για Σκλαβενίτη, ΑΒ, Μασούτη κ.λπ. δοκιμάζουμε requests με κανονικά headers περιήγησης
def scrape_with_requests(url, supermarket_name):
    print(f"Συλλογή από {supermarket_name} (Requests mode)...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "el-GR,el;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"-> Αποτυχία {supermarket_name}: Status code {response.status_code}")
            return []
            
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        raw = []
        # Ψάχνουμε γενικά για κάρτες προϊόντων
        elements = soup.select('article, div.product, div[class*="product"], div[class*="item"]')
        for el in elements:
            text = el.get_text(separator=' | ', strip=True)
            if text and '€' in text and len(text) < 300 and len(text) > 10:
                img = el.find('img')
                imgSrc = ""
                if img:
                    imgSrc = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                    if imgSrc.startswith('//'):
                        imgSrc = 'https:' + imgSrc
                
                if not any(r['text'] == text for r in raw):
                    raw.append({ "text": text, "image": imgSrc })
                    
        parsed = parse_products(raw, supermarket_name)
        print(f"-> Επιτυχία: {len(parsed)} προϊόντα από {supermarket_name}.")
        return parsed
    except Exception as e:
        print(f"Σφάλμα {supermarket_name}: {e}")
        return []

# Εκτέλεση όλων
with sync_playwright() as p:
    all_offers = []
    
    # Κρητικός (Playwright)
    all_offers.extend(scrape_kritikos(p))
    
    # Υπόλοιπα καταστήματα με Requests mode για αποφυγή headless blocks
    all_offers.extend(scrape_with_requests("https://www.sklavenitis.gr/prosporous-prosfores/", "Σκλαβενίτης"))
    all_offers.extend(scrape_with_requests("https://www.ab.gr/e-shop/prosfopoi-prosfores", "ΑΒ Βασιλόπουλος"))
    all_offers.extend(scrape_with_requests("https://www.masoutis.gr/offers", "Μασούτης"))
    all_offers.extend(scrape_with_requests("https://www.galaxiasnet.gr/", "Γαλαξίας"))
    all_offers.extend(scrape_with_requests("https://www.mymarket.gr/", "My Market"))
    all_offers.extend(scrape_with_requests("https://www.lidl.gr/", "Lidl"))

    unique_offers = []
    seen_titles = set()
    for offer in all_offers:
        key = (offer["supermarket"], offer["title"])
        if key not in seen_titles:
            seen_titles.add(key)
            unique_offers.append(offer)

    with open("clean_offers.json", "w", encoding="utf-8") as f:
        json.dump(unique_offers, f, ensure_ascii=False, indent=4)
        print(f"\nΑποθήκευση {len(unique_offers)} συνολικών μοναδικών προσφορών στο clean_offers.json!")
