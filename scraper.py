from playwright.sync_api import sync_playwright
import json
import re

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
    try:
        page.goto("https://www.sklavenitis.gr/prosporous-prosfores/", timeout=60000)
        page.wait_for_timeout(5000)
    except:
        return []
    
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)
        
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], div[class*="item"]');
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
        page.goto("https://www.ab.gr/e-shop/prosfopoi-prosfores", timeout=60000)
        page.wait_for_timeout(5000)
    except:
        return []
        
    for _ in range(3):
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
    parsed = parse_products(raw, "ΑΒ Βασιλόπουλος")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από ΑΒ.")
    return parsed

def scrape_masoutis(page):
    print("Συλλογή από Μασούτη...")
    try:
        page.goto("https://www.masoutis.gr/offers", timeout=60000)
        page.wait_for_timeout(5000)
    except:
        return []
        
    for _ in range(3):
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
        page.goto("https://www.galaxiasnet.gr/", timeout=60000)
        page.wait_for_timeout(5000)
    except:
        return []
        
    for _ in range(3):
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
    parsed = parse_products(raw, "Γαλαξίας")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Γαλαξία.")
    return parsed

def scrape_mymarket(page):
    print("Συλλογή από My Market...")
    try:
        page.goto("https://www.mymarket.gr/", timeout=60000)
        page.wait_for_timeout(5000)
    except:
        return []
        
    for _ in range(3):
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
    parsed = parse_products(raw, "My Market")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από My Market.")
    return parsed

def scrape_lidl(page):
    print("Συλλογή από Lidl...")
    try:
        page.goto("https://www.lidl.gr/", timeout=60000)
        page.wait_for_timeout(5000)
    except:
        return []
        
    for _ in range(3):
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
    parsed = parse_products(raw, "Lidl")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Lidl.")
    return parsed

# Εκτέλεση για όλα τα σούπερ μάρκετ
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    all_offers = []
    all_offers.extend(scrape_sklavenitis(page))
    all_offers.extend(scrape_ab(page))
    all_offers.extend(scrape_masoutis(page))
    all_offers.extend(scrape_kritikos(page))
    all_offers.extend(scrape_galaxias(page))
    all_offers.extend(scrape_mymarket(page))
    all_offers.extend(scrape_lidl(page))

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
        print(f"\nΑποθήκευση {len(unique_offers)} συνολικών μοναδικών προσφορών στο clean_offers.json!")
