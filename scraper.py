from playwright.sync_api import sync_playwright
import json
import re

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

def create_stealth_page(p):
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080"
        ]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="el-GR",
        timezone_id="Europe/Athens"
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return browser, page

def scrape_sklavenitis(p):
    print("Συλλογή από Σκλαβενίτη...")
    browser, page = create_stealth_page(p)
    try:
        # Δοκιμάζουμε απευθείας την κεντρική σελίδα προσφορών με μεγαλύτερο timeout
        page.goto("https://www.sklavenitis.gr/prosporous-prosfores/", timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Σφάλμα πλοήγησης Σκλαβενίτης: {e}")
        browser.close()
        return []
    
    # Scroll για να φορτώσουν τα δυναμικά προϊόντα (Lazy loading)
    for _ in range(5):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2500)
        
    raw = page.evaluate("""() => {
        const results = [];
        // Ψάχνουμε για ευρύτερα containers προϊόντων στον Σκλαβενίτη
        const elements = document.querySelectorAll('article, div[class*="product"], div.item, li[class*="product"]');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 300 && text.length > 10) {
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
    browser.close()
    parsed = parse_products(raw, "Σκλαβενίτης")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Σκλαβενίτη.")
    return parsed

def scrape_ab(p):
    print("Συλλογή από ΑΒ Βασιλόπουλο...")
    browser, page = create_stealth_page(p)
    try:
        page.goto("https://www.ab.gr/e-shop/prosfopoi-prosfores", timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Σφάλμα πλοήγησης ΑΒ: {e}")
        browser.close()
        return []
        
    for _ in range(5):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2500)
        
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], app-product-tile, div[data-productid]');
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
    browser.close()
    parsed = parse_products(raw, "ΑΒ Βασιλόπουλος")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από ΑΒ.")
    return parsed

def scrape_masoutis(p):
    print("Συλλογή από Μασούτη...")
    browser, page = create_stealth_page(p)
    try:
        page.goto("https://www.masoutis.gr/offers", timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Σφάλμα πλοήγησης Μασούτης: {e}")
        browser.close()
        return []
        
    for _ in range(5):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2500)
        
    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], div[class*="item"]');
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
    browser.close()
    parsed = parse_products(raw, "Μασούτης")
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από Μασούτη.")
    return parsed
