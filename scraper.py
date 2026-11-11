
import json
import os
import re
from datetime import datetime
from ftplib import FTP
from playwright.sync_api import sync_playwright

TARGET_URLS = {
    "Μασούτης": "https://www.masoutis.gr/eshop",
    "Σκλαβενίτης": "https://www.sklavenitis.gr/e-shop/",
    "Lidl": "https://www.lidl-hellas.gr/c/store/evdomadiaies-epiloges-26kw45/a10106403",
    "MyMarket": "https://www.mymarket.gr/offers",
    "ΑΒ Βασιλόπουλος": "https://www.ab.gr/search/promotions"
}

TODAY = datetime.now().strftime("%Y-%m-%d")


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def scrape_special_market(page, market_name, url):
    print(f"  [INFO] Ειδικός scraper: {market_name}")

    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    # Αποδοχή cookies
    for selector in [
        "#onetrust-accept-btn-handler",
        "button:has-text('Αποδοχή')",
        "button:has-text('Συμφωνώ')",
        "button:has-text('Accept All')"
    ]:
        try:
            btn = page.locator(selector).first
            if btn.count() and btn.is_visible():
                btn.click(timeout=2000)
                page.wait_for_timeout(1500)
                break
        except Exception:
            pass

    # Lazy loading προϊόντων
    for _ in range(12):
        page.mouse.wheel(0, 1800)
        page.wait_for_timeout(900)

    # Εντοπισμός πιθανών product cards
    products = page.evaluate("""() => {
        const priceRegex = /(?:\\d{1,4}[.,]\\d{2})\\s*€/;
        const selectors = [
            '[data-testid*="product"]',
            '[class*="product-card"]',
            '[class*="ProductCard"]',
            '[class*="product-item"]',
            '[class*="ProductItem"]',
            'article'
        ];

        let cards = [];

        for (const selector of selectors) {
            cards.push(...document.querySelectorAll(selector));
        }

        if (!cards.length) {
            cards = Array.from(document.querySelectorAll('div, li'))
                .filter(el => {
                    const text = el.innerText || '';
                    return text.length > 30 &&
                           text.length < 800 &&
                           priceRegex.test(text) &&
                           el.querySelector('img');
                });
        }

        const result = [];
        const seen = new Set();

        for (const card of cards) {
            const text = (card.innerText || '').trim();

            if (!text || text.length > 1200) continue;

            const priceMatch = text.match(priceRegex);
            if (!priceMatch) continue;

            const img = card.querySelector('img');
            const image = img?.getAttribute('src') ||
                         img?.getAttribute('data-src') ||
                         img?.getAttribute('data-lazy-src') ||
                         img?.getAttribute('data-original') || '';

            const heading = card.querySelector(
                'h2, h3, h4, [class*="product-name"], ' +
                '[class*="product-title"], [class*="ProductName"]'
            );

            let title = heading?.innerText?.trim() ||
                        img?.getAttribute('alt') || '';

            if (!title) {
                const lines = text.split('\\n')
                    .map(x => x.trim())
                    .filter(x => x.length > 4);

                title = lines.find(x =>
                    !priceRegex.test(x) &&
                    !/καλάθι|προσθήκη|ποσότητα|cookies/i.test(x)
                ) || '';
            }

            const link = card.querySelector('a[href]');

            title = title.replace(/\\s+/g, ' ').trim();

            if (!title || title.length < 3) continue;

            const key = title.toLowerCase() + priceMatch[0];

            if (seen.has(key)) continue;
            seen.add(key);

            result.push({
                title,
                price: priceMatch[0].trim(),
                image,
                url: link?.href || ''
            });
        }

        return result;
    }""")

    offers = []

    for p in products:
        image = p.get("image", "")

        if image.startswith("//"):
            image = "https:" + image

        offers.append({
            "supermarket": market_name,
            "title": clean_text(p["title"]),
            "price": p["price"],
            "old_price": "",
            "image": image or "https://via.placeholder.com/150",
            "date": TODAY,
            "url": p.get("url", "")
        })

    print(f"  [OK] {market_name}: {len(offers)} προϊόντα")
    return offers


def scrape_generic_market(page, market_name, url):
    print(f"  [INFO] Γενικός scraper: {market_name}")

    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    for _ in range(8):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(800)

    cards = page.locator(
        "article, [class*='product-card'], "
        "[class*='product-item'], [class*='ProductCard']"
    ).all()

    offers = []
    seen = set()

    for card in cards[:250]:
        try:
            text = clean_text(card.inner_text())

            match = re.search(r"\d{1,4}[.,]\d{2}\s*€", text)
            if not match:
                continue

            heading = card.locator(
                "h2, h3, h4, [class*='title'], [class*='name']"
            ).first

            title = ""

            if heading.count():
                title = clean_text(heading.inner_text())

            if not title:
                title = text.split(match.group())[0].strip()

            if not title or len(title) < 3:
                continue

            key = title.lower()

            if key in seen:
                continue

            seen.add(key)

            img = card.locator("img").first
            image = ""

            if img.count():
                image = (
                    img.get_attribute("src") or
                    img.get_attribute("data-src") or ""
                )

            if image.startswith("//"):
                image = "https:" + image

            offers.append({
                "supermarket": market_name,
                "title": title,
                "price": match.group().strip(),
                "old_price": "",
                "image": image or "https://via.placeholder.com/150",
                "date": TODAY
            })

        except Exception:
            continue

    print(f"  [OK] {market_name}: {len(offers)} προϊόντα")
    return offers


def scrape_all_supermarkets():
    print("=== ΕΝΑΡΞΗ SCRAPER ===")

    all_offers = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="el-GR",
            timezone_id="Europe/Athens"
        )

        page = context.new_page()

        for market_name, url in TARGET_URLS.items():
            try:
                print(f"-> {market_name}")

                if market_name in ["Μασούτης", "Σκλαβενίτης"]:
                    offers = scrape_special_market(
                        page, market_name, url
                    )
                else:
                    offers = scrape_generic_market(
                        page, market_name, url
                    )

                all_offers.extend(offers)

            except Exception as e:
                print(f"[ERROR] {market_name}: {e}")

        browser.close()

    data = {
        "updated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "total_offers": len(all_offers),
        "offers": all_offers
    }

    filename = "clean_offers.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[OK] {len(all_offers)} προϊόντα συνολικά")
    return filename


def upload_all_to_ftp():
    print("=== FTP UPLOAD ===")

    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("[ERROR] Λείπουν FTP credentials")
        return

    try:
        with FTP(ftp_server, timeout=30) as ftp:
            ftp.login(ftp_user, ftp_pass)

            ftp.cwd("prosfores.infy.click")
            ftp.cwd("htdocs")

            with open("clean_offers.json", "rb") as f:
                ftp.storbinary("STOR clean_offers.json", f)

            print("[OK] clean_offers.json ανέβηκε στο FTP")

    except Exception as e:
        print(f"[ERROR] FTP: {e}")


if __name__ == "__main__":
    scrape_all_supermarkets()
    upload_all_to_ftp()
