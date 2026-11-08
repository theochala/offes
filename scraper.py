from playwright.sync_api import sync_playwright
import json
import re

def clean_title(title):
    # Καθαρισμός από περιττές λέξεις, εικονίδια και UI artifacts
    artifacts = [
        "playlist_add", "favorite", "add", "remove", "Χρυσές Τιμές", 
        "Λίτ", "Τεμ", "/", "Νέο", "Προσωρινά μη διαθέσιμο", "Διαφήμιση"
    ]
    for art in artifacts:
        title = title.replace(art, "")
    
    # Αφαίρεση διπλότυπων λέξεων/φράσεων που επαναλαμβάνονται
    words = title.split()
    seen = []
    for w in words:
        if w not in seen or len(w) > 4: # Επιτρέπουμε μικρές λέξεις αν δεν είναι συνεχόμενες
            seen.append(w)
    
    title = " ".join(seen)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def parse_products(raw_products, supermarket_name):
    parsed = []
    for item in raw_products:
        text = item["text"]
        img_url = item["image"]
        
        # Εύρεση τιμών (π.χ. 1,50 € ή 1.50 €)
        prices = re.findall(r'(\d+[\.,]\d+\s*€)', text)
        title = text
        for price in prices:
            title = title.replace(price, "")
            
        title = clean_title(title)
        
        price_val = prices[-1] if prices else ""
        
        # Αυστηροί έλεγχοι εγκυρότητας
        if len(title) > 5 and prices and price_val != "0,00 €" and img_url and img_url.startswith('http'):
            # Αποφυγή διπλοεγγραφών στο ίδιο supermarket
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
        // Στοχεύουμε πιο κοντά στις κάρτες προϊόντων για να αποφύγουμε τα διπλά
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

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=50)
    page = browser.new_page()
    
    all_offers = []
    
    for scraper_func in [scrape_sklavenitis, scrape_ab, scrape_masoutis, scrape_kritikos, scrape_galaxias, scrape_mymarket]:
        try:
            all_offers.extend(scraper_func(page))
        except Exception as e:
            print("Σφάλμα:", e)

    browser.close()
    
    # Τελικό καθαρισμό παγκόσμιας μοναδικότητας (αν υπάρχει ξανά διπλότυπο τίτλου)
    unique_offers = []
    seen_titles = set()
    for offer in all_offers:
        key = (offer["supermarket"], offer["title"])
        if key not in seen_titles:
            seen_titles.add(key)
            unique_offers.append(offer)

    with open("clean_offers.json", "w", encoding="utf-8") as f:
        json.dump(unique_offers, f, ensure_ascii=False, indent=4)
        print(f"\nΣυνολική αποθήκευση {len(unique_offers)} μοναδικών και καθαρών προϊόντων στο clean_offers.json!")