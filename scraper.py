
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


def today():
    return datetime.now().strftime("%Y-%m-%d")


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_image(image):
    if not image:
        return ""
    if image.startswith("//"):
        return "https:" + image
    return image


# ==========================================
# ΜΑΣΟΥΤΗΣ & ΣΚΛΑΒΕΝΙΤΗΣ
# ==========================================

def scrape_special_market(page, market_name, url):
    print(f"  [INFO] Ειδικός scraper: {market_name}")

    offers = []
    seen = set()

    # ======================================
    # ΣΚΛΑΒΕΝΙΤΗΣ
    # ======================================

    if market_name == "Σκλαβενίτης":

        base = "https://www.sklavenitis.gr/"

        for page_num in range(1, 16):

            api_url = (
                base
                + "?$component=Atcom.Sites.Yoda.Components."
                + "ProductList.Index"
                + "&sortby=ByPopularity"
                + f"&pg={page_num}"
                + "&endless=true"
            )

            try:
                page.goto(
                    api_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                page.wait_for_timeout(2500)

                products = page.evaluate("""() => {

                    const result = [];

                    const cards = document.querySelectorAll(
                        'article, [class*="product"], [class*="Product"]'
                    );

                    for (const card of cards) {

                        const text = card.innerText || '';

                        const price = text.match(
                            /\\d{1,4}[.,]\\d{2}\\s*€/
                        );

                        if (!price) continue;

                        const img = card.querySelector('img');

                        const heading = card.querySelector(
                            'h2,h3,h4,[class*="title"],[class*="name"]'
                        );

                        const title =
                            heading?.innerText?.trim() ||
                            img?.alt ||
                            '';

                        const link = card.querySelector('a[href]');

                        if (!title) continue;

                        result.push({
                            title: title,
                            price: price[0],
                            image: img?.src || '',
                            url: link?.href || ''
                        });
                    }

                    return result;

                }""")

                if not products:
                    print(
                        f"  [INFO] Σκλαβενίτης page "
                        f"{page_num}: 0 προϊόντα"
                    )
                    continue

                for product in products:

                    title = clean_text(product["title"])
                    key = title.lower()

                    if not title or key in seen:
                        continue

                    seen.add(key)

                    offers.append({
                        "supermarket": market_name,
                        "title": title,
                        "price": product["price"],
                        "old_price": "",
                        "image": normalize_image(product["image"])
                            or "https://via.placeholder.com/150",
                        "date": today(),
                        "url": product["url"]
                    })

            except Exception as e:
                print(
                    f"  [ERROR] Σκλαβενίτης page "
                    f"{page_num}: {e}"
                )

        print(
            f"  [OK] Σκλαβενίτης: "
            f"{len(offers)} προϊόντα"
        )

        return offers

    # ======================================
    # ΜΑΣΟΥΤΗΣ
    # ======================================

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(6000)

    # Cookies
    for selector in [
        "#onetrust-accept-btn-handler",
        "button:has-text('Αποδοχή')",
        "button:has-text('Συμφωνώ')",
        "button:has-text('Accept All')"
    ]:

        try:
            button = page.locator(selector).first

            if button.count() and button.is_visible():
                button.click(timeout=2000)
                page.wait_for_timeout(1500)
                break

        except Exception:
            pass

    # Lazy loading
    for _ in range(12):
        page.mouse.wheel(0, 1800)
        page.wait_for_timeout(1000)

    products = page.evaluate("""() => {

        const result = [];

        const cards = document.querySelectorAll(
            'article, [class*="product"], [class*="Product"]'
        );

        for (const card of cards) {

            const text = card.innerText || '';

            const price = text.match(
                /\\d{1,4}[.,]\\d{2}\\s*€/
            );

            if (!price) continue;

            const img = card.querySelector('img');

            const heading = card.querySelector(
                'h2,h3,h4,[class*="title"],[class*="name"]'
            );

            const title =
                heading?.innerText?.trim() ||
                img?.alt ||
                '';

            const link = card.querySelector('a[href]');

            if (!title) continue;

            result.push({
                title: title,
                price: price[0],
                image: img?.src || '',
                url: link?.href || ''
            });
        }

        return result;

    }""")

    for product in products:

        title = clean_text(product["title"])
        key = title.lower()

        if not title or key in seen:
            continue

        seen.add(key)

        offers.append({
            "supermarket": market_name,
            "title": title,
            "price": product["price"],
            "old_price": "",
            "image": normalize_image(product["image"])
                or "https://via.placeholder.com/150",
            "date": today(),
            "url": product["url"]
        })

    print(f"  [OK] Μασούτης: {len(offers)} προϊόντα")

    return offers


# ==========================================
# LIDL, MYMARKET, ΑΒ
# ==========================================

def scrape_generic_market(page, market_name, url):

    print(f"  [INFO] Γενικός scraper: {market_name}")

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(6000)

    # Cookies
    for selector in [
        "#onetrust-accept-btn-handler",
        "button:has-text('Αποδοχή')",
        "button:has-text('Συμφωνώ')"
    ]:

        try:
            button = page.locator(selector).first

            if button.count() and button.is_visible():
                button.click(timeout=2000)
                break

        except Exception:
            pass

    for _ in range(10):
        page.mouse.wheel(0, 1800)
        page.wait_for_timeout(900)

    cards = page.locator(
        "article, [class*='product-card'], "
        "[class*='product-item'], [class*='ProductCard'], "
        "[data-testid*='product']"
    ).all()

    offers = []
    seen = set()

    for card in cards[:300]:

        try:

            text = clean_text(card.inner_text())

            price_match = re.search(
                r"\\d{1,4}[.,]\\d{2}\\s*€",
                text
            )

            if not price_match:
                continue

            heading = card.locator(
                "h2,h3,h4,[class*='title'],[class*='name']"
            ).first

            title = ""

            if heading.count():
                title = clean_text(heading.inner_text())

            if not title:
                title = text.split(price_match.group())[0].strip()

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
                    img.get_attribute("src")
                    or img.get_attribute("data-src")
                    or img.get_attribute("data-lazy-src")
                    or ""
                )

            image = normalize_image(image)

            link = card.locator("a[href]").first

            product_url = ""

            if link.count():
                product_url = link.get_attribute("href") or ""

            offers.append({
                "supermarket": market_name,
                "title": title,
                "price": price_match.group().strip(),
                "old_price": "",
                "image": image
                    or "https://via.placeholder.com/150",
                "date": today(),
                "url": product_url
            })

        except Exception:
            continue

    print(
        f"  [OK] {market_name}: "
        f"{len(offers)} προϊόντα"
    )

    return offers


# ==========================================
# MAIN SCRAPER
# ==========================================

def scrape_all_supermarkets():

    print("=== ΕΝΑΡΞΗ SCRAPER ===")

    all_offers = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox"
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={
                "width": 1920,
                "height": 1080
            },
            locale="el-GR",
            timezone_id="Europe/Athens"
        )

        page = context.new_page()

        for market_name, url in TARGET_URLS.items():

            try:

                print(f"-> {market_name}")

                if market_name in [
                    "Μασούτης",
                    "Σκλαβενίτης"
                ]:

                    offers = scrape_special_market(
                        page,
                        market_name,
                        url
                    )

                else:

                    offers = scrape_generic_market(
                        page,
                        market_name,
                        url
                    )

                all_offers.extend(offers)

            except Exception as e:

                print(
                    f"[ERROR] {market_name}: {e}"
                )

        browser.close()

    data = {
        "updated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "total_offers": len(all_offers),
        "offers": all_offers
    }

    filename = "clean_offers.json"

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )

    print(
        f"=== ΟΛΟΚΛΗΡΩΘΗΚΕ: "
        f"{len(all_offers)} προϊόντα ==="
    )

    return filename


# ==========================================
# FTP UPLOAD
# ==========================================

def upload_all_to_ftp():

    print("=== FTP UPLOAD ===")

    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([
        ftp_server,
        ftp_user,
        ftp_pass
    ]):

        print("[ERROR] Λείπουν FTP credentials")
        return

    try:

        with FTP(
            ftp_server,
            timeout=30
        ) as ftp:

            ftp.login(
                user=ftp_user,
                passwd=ftp_pass
            )

            ftp.cwd("prosfores.infy.click")
            ftp.cwd("htdocs")

            with open(
                "clean_offers.json",
                "rb"
            ) as f:

                ftp.storbinary(
                    "STOR clean_offers.json",
                    f
                )

            print(
                "[OK] clean_offers.json ανέβηκε στο FTP"
            )

    except Exception as e:

        print(f"[ERROR] FTP: {e}")


# ==========================================
# EXECUTION
# ==========================================

if __name__ == "__main__":

    scrape_all_supermarkets()
    upload_all_to_ftp()
