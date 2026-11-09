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

def get_browser_page(p):
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--disable-dev-shm-usage"
        ]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="el-GR",
        timezone_id="Europe/Athens"
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return browser, page

def scrape_generic(p, name, url):
    print(f"Συλλογή από {name}...")
    browser, page = get_browser_page(p)
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(7000)
    except Exception as e:
        print(f"Σφάλμα σύνδεσης στο {name}: {e}")
        browser.close()
        return []

    # Scroll down to trigger lazy loading
    for _ in range(4):
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)

    raw = page.evaluate("""() => {
        const results = [];
        const elements = document.querySelectorAll('article, div[class*="product"], div[class*="item"], li[class*="product"]');
        elements.forEach(el => {
            const text = el.innerText;
            if (text && text.includes('€') && text.length < 350 && text.length > 8) {
                const cleanText = text.replace(/\\n/g, ' | ').trim();
                const img = el.querySelector('img');
                let imgSrc = img ? (img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '') : '';
                
                if (imgSrc.startsWith('//')) {
                    imgSrc = 'https:' + imgSrc;
                }
                
                if (!results.some(r => r.text === cleanText)) {
                    results.push({ text: cleanText, image: imgSrc });
                }
            }
        });
        return results;
    }""")
    browser.close()
    parsed = parse_products(raw, name)
    print(f"-> Επιτυχία: {len(parsed)} προϊόντα από {name}.")
    return parsed

# Εκτέλεση για όλα τα καταστήματα με τις σωστές διευθύνσεις προσφορών
with sync_playwright() as p:
    all_offers = []
    
    # 1. Κρητικός
    all_offers.extend(scrape_generic(p, "Κρητικός", "https://kritikos-sm.gr/offers/"))
    
    # 2. Σκλαβενίτης (Χρησιμοποιούμε την κεντρική και εναλλακτική σελίδα προσφορών)
    all_offers.extend(scrape_generic(p, "Σκλαβενίτης", "https://www.sklavenitis.gr/prosporous-prosfores/"))
    
    # 3. ΑΒ Βασιλόπουλος
    all_offers.extend(scrape_generic(p, "ΑΒ Βασιλόπουλος", "https://www.ab.gr/e-shop/prosfopoi-prosfores"))
    
    # 4. Μασούτης
    all_offers.extend(scrape_generic(p, "Μασούτης", "https://www.masoutis.gr/offers"))
    
    # 5. Γαλαξίας
    all_offers.extend(scrape_generic(p, "Γαλαξίας", "https://www.galaxiasnet.gr/"))
    
    # 6. My Market
    all_offers.extend(scrape_generic(p, "My Market", "https://www.mymarket.gr/"))
    
    # 7. Lidl
    all_offers.extend(scrape_generic(p, "Lidl", "https://www.lidl.gr/"))

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
