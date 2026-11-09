import json
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def clean_title(title):
    artifacts = [
        "playlist_add", "favorite", "add", "remove", "Χρυσές Τιμές", 
        "Λίτ", "Τεμ", "/", "Νέο", "Προσωρινά μη διαθέσιμο", "Διαφήμιση",
        "με Lidl Plus", "Χωρίς Lidl Plus", "Προσθήκη", "Καλάθι"
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
    invalid_keywords = [
        "Διαγωνισμοί", "ώρα παράδοσης", "items in cart", "Επίλεξε", 
        "Σούπερ Μάρκετ", "Καλάθι", "Σύνδεση", "Εγγραφή", "Cookies", "Πολιτική"
    ]
    
    for item in raw_products:
        text = item["text"]
        img_url = item["image"]
        
        if any(kw.lower() in text.lower() for kw in invalid_keywords):
            continue
            
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

# 1. Κρητικός (Playwright)
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

# 2. Εναλλακτική μέθοδος με direct lightweight requests και mobile user agents για τα υπόλοιπα
def scrape_lightweight(url, supermarket_name):
    print(f"Συλλογή από {supermarket_name}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "el-GR,el;q=0.9"
    }
    
    try:
        # Χρησιμοποιούμε μικρό timeout και custom headers κινητού που συχνά εξαιρούνται από τα αυστηρά browser blocks
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"-> Παράκαμψη {supermarket_name} (Status {response.status_code})")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        raw = []
        elements = soup.select('article, div.product, div[class*="product"], div[class*="item"], li[class*="product"], div.box')
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
        print(f"-> Χωρίς άμεση απόκριση από {supermarket_name} (Timeout/Blocked).")
        return []

# Εκτέλεση για ΟΛΑ τα σούπερ μάρκετ
with sync_playwright() as p:
    all_offers = []
    
    # 1. Κρητικός
    all_offers.extend(scrape_kritikos(p))
    
    # 2. Υπόλοιπα καταστήματα με lightweight mobile requests
    all_offers.extend(scrape_lightweight("https://www.sklavenitis.gr/prosporous-prosfores/", "Σκλαβενίτης"))
    all_offers.extend(scrape_lightweight("https://www.ab.gr/e-shop/prosfopoi-prosfores", "ΑΒ Βασιλόπουλος"))
    all_offers.extend(scrape_lightweight("https://www.masoutis.gr/offers", "Μασούτης"))
    all_offers.extend(scrape_lightweight("https://www.galaxiasnet.gr/", "Γαλαξίας"))
    all_offers.extend(scrape_lightweight("https://www.mymarket.gr/", "My Market"))
    all_offers.extend(scrape_lightweight("https://www.lidl.gr/c/prosfores/s10007771", "Lidl"))

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
