import json
import os
import re
from datetime import datetime
from ftplib import FTP
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

TARGET_URLS = {
    "Lidl": "https://www.lidl-hellas.gr/c/store/evdomadiaies-epiloges-26kw45/a10106403",
    "MyMarket": "https://www.mymarket.gr/offers",
    "ΑΒ Βασιλόπουλος": "https://www.ab.gr/search/promotions",
}

OUTPUT_FILE = Path("clean_offers.json")
DEBUG_DIR = Path("debug_html")

PRICE_REGEX = re.compile(
    r"(?<!\d)(\d{1,4}[,.]\d{2})\s*€?"
)

EXCLUDED_WORDS = [
    "καλάθι", "σούπερ", "αρχική", "σύνδεση",
    "προσφορές", "cookies", "newsletter",
    "εγγραφή", "αποδοχή", "απόρριψη",
    "λεπτομέρειες", "αναζήτηση", "μενού",
    "προϊόντα", "φίλτρα", "ταξινόμηση",
]


def clean_text(value):
    if not value:
        return ""
    return " ".join(str(value).split()).strip()


def is_valid_title(title):
    title = clean_text(title)
    if len(title) < 4 or len(title) > 180:
        return False
    if PRICE_REGEX.search(title):
        return False
    lowered = title.lower()
    if any(word in lowered for word in EXCLUDED_WORDS):
        return False
    return True


def extract_price(text):
    if not text:
        return ""
    match = PRICE_REGEX.search(text)
    if not match:
        return ""
    number = match.group(1).replace(",", ".")
    try:
        value = float(number)
    except ValueError:
        return ""
    if value <= 0 or value > 10000:
        return ""
    return match.group(1).replace(".", ",") + " €"


def parse_products_generic(raw_items, market_name):
    offers = []
    for item in raw_items:
        text = item.get("text", "")
        image = item.get("image", "")

        price = extract_price(text)
        if not price:
            continue

        # Καθαρισμός τίτλου από το κείμενο αφαίρεώντας την τιμή
        title_candidate = text.replace(price, "").replace("€", "").strip()
        parts = [p.strip() for p in title_candidate.split(" | ") if len(p.strip()) > 3]
        
        title = ""
        for p in parts:
            if is_valid_title(p):
                title = p
                break
        
        if not title and parts:
            title = parts[0]

        if is_valid_title(title):
            offers.append({
                "supermarket": market_name,
                "title": title,
                "price": price,
                "old_price": "",
                "image": image if image else "https://via.placeholder.com/150?text=Offer",
                "date": datetime.now().strftime("%Y-%m-%d"),
            })
    return offers


# Η ακριβής λογική που σου δούλευε τοπικά για τον Μασούτη
def scrape_masoutis(page):
    print("\n-> Μασούτης: https://www.masoutis.gr/offers")
    try:
        page.goto("https://www.masoutis.gr/offers", wait_until="domcontentloaded", timeout=60000)
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
        
        parsed = parse_products_generic(raw, "Μασούτης")
        print(f"  [OK] Μασούτης: Εξήχθησαν {len(parsed)} προϊόντα.")
        return parsed
    except Exception as e:
        print(f"  [X] Σφάλμα στον Μασούτη: {e}")
        return []


def extract_image(card, page_url):
    image = card.find("img")
    if not image:
        return ""
    possible_sources = [
        image.get("src"),
        image.get("data-src"),
        image.get("data-lazy-src"),
        image.get("data-original"),
        image.get("data-image"),
    ]
    srcset = image.get("srcset") or image.get("data-srcset")
    if srcset:
        try:
            first_source = srcset.split(",")[0].strip().split(" ")[0]
            possible_sources.append(first_source)
        except Exception:
            pass

    for source in possible_sources:
        if not source:
            continue
        source = source.strip()
        if source.startswith("data:"):
            continue
        return urljoin(page_url, source)
    return ""


def extract_title(card):
    selectors = [
        "h1", "h2", "h3", "h4",
        '[class*="product-title"]', '[class*="productTitle"]',
        '[class*="product-name"]', '[class*="productName"]',
        '[class*="item-title"]', '[class*="item-name"]',
        '[data-testid*="title"]', "a"
    ]
    for selector in selectors:
        for element in card.select(selector):
            candidate = clean_text(element.get_text(" ", strip=True))
            if is_valid_title(candidate):
                return candidate
    image = card.find("img")
    if image:
        alt = clean_text(image.get("alt", ""))
        if is_valid_title(alt):
            return alt
    return ""


def extract_old_price(card, current_price):
    old_price_selectors = [
        "del", "s", "strike",
        '[class*="old-price"]', '[class*="oldPrice"]',
        '[class*="original-price"]', '[class*="price-old"]',
        '[class*="previous-price"]',
    ]
    for selector in old_price_selectors:
        for element in card.select(selector):
            price = extract_price(element.get_text(" ", strip=True))
            if price and price != current_price:
                return price
    return ""


def parse_html_products(html_content, market_name, page_url):
    soup = BeautifulSoup(html_content, "html.parser")
    offers = []
    seen = set()

    selectors = [
        '[data-testid*="product"]',
        '[class*="product-card"]',
        '[class*="productCard"]',
        '[class*="product-item"]',
        '[class*="productItem"]',
        '[class*="product-tile"]',
        '[class*="productTile"]',
        "article",
        "li[class*='product']",
        "div[class*='product']",
        "div[class*='item']",
    ]

    cards = []
    for selector in selectors:
        try:
            found = soup.select(selector)
            for card in found:
                if card not in cards:
                    cards.append(card)
        except Exception:
            continue

    for card in cards[:600]:
        try:
            card_text = clean_text(card.get_text(" ", strip=True))
            if not card_text:
                continue
            price = extract_price(card_text)
            if not price:
                continue
            title = extract_title(card)
            if not title:
                continue
            image = extract_image(card, page_url)
            old_price = extract_old_price(card, price)

            key = (market_name, title.lower(), price)
            if key in seen:
                continue
            seen.add(key)

            offers.append({
                "supermarket": market_name,
                "title": title,
                "price": price,
                "old_price": old_price,
                "image": image,
                "date": datetime.now().strftime("%Y-%m-%d"),
            })
        except Exception:
            continue

    return offers


def scrape_market(page, market_name, url):
    print(f"\n-> {market_name}: {url}")
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        status = response.status if response else 0
        print(f"  HTTP Status: {status}")

        if status >= 400:
            print(f"  [!] HTTP σφάλμα: {status}")
            return []

        page.wait_for_timeout(5000)

        try:
            cookie_button = page.locator(
                "button:has-text('Αποδοχή'), "
                "button:has-text('Συμφωνώ'), "
                "#onetrust-accept-btn-handler"
            ).first
            if cookie_button.count() > 0:
                cookie_button.click(timeout=2000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        for _ in range(8):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(1000)

        html = page.content()
        offers = parse_html_products(html, market_name, page.url)

        if offers:
            print(f"  [OK] {market_name}: Εξήχθησαν {len(offers)} προϊόντα.")
        else:
            print(f"  [!] {market_name}: 0 προϊόντα.")

        return offers
    except Exception as error:
        print(f"  [X] Σφάλμα στο {market_name}: {error}")
        return []


def scrape_all_supermarkets():
    print("=== ΕΝΑΡΞΗ SCRAPER ===")
    all_offers = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="el-GR",
            timezone_id="Europe/Athens",
        )
        page = context.new_page()

        # 1. Εκτέλεση της δοκιμασμένης μεθόδου για τον Μασούτη
        masoutis_offers = scrape_masoutis(page)
        all_offers.extend(masoutis_offers)

        # 2. Εκτέλεση των υπόλοιπων καταστημάτων
        for market_name, url in TARGET_URLS.items():
            offers = scrape_market(page, market_name, url)
            all_offers.extend(offers)

        browser.close()

    unique_offers = []
    seen = set()
    for offer in all_offers:
        key = (offer["supermarket"], offer["title"].lower(), offer["price"])
        if key not in seen:
            seen.add(key)
            unique_offers.append(offer)

    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_offers": len(unique_offers),
        "offers": unique_offers,
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    print(f"\n=== ΟΛΟΚΛΗΡΩΘΗΚΕ ===")
    print(f"Συνολικά προϊόντα: {len(unique_offers)}")
    return str(OUTPUT_FILE)


def upload_all_to_ftp():
    print("\n=== ΜΕΤΑΦΟΡΤΩΣΗ FTP ===")
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("[!] Λείπουν τα FTP στοιχεία.")
        return

    if not OUTPUT_FILE.exists():
        return

    try:
        ftp = FTP(ftp_server, timeout=30)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        ftp.cwd("prosfores.infy.click")
        ftp.cwd("htdocs")

        with OUTPUT_FILE.open("rb") as file:
            ftp.storbinary("STOR clean_offers.json", file)
        print("[OK] Ανέβηκε το clean_offers.json.")
        ftp.quit()
    except Exception as error:
        print(f"[X] Σφάλμα FTP: {error}")


if __name__ == "__main__":
    scrape_all_supermarkets()
    upload_all_to_ftp()
