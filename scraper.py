
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_FILE = Path("clean_offers.json")

SUPERMARKETS = {
    "Μασούτης": "https://www.masoutis.gr/eshop",
    "Σκλαβενίτης": "https://www.sklavenitis.gr/e-shop/",
    "Lidl": "https://www.lidl-hellas.gr/c/store/evdomadiaies-epiloges-26kw45/a10106403",
    "MyMarket": "https://www.mymarket.gr/offers",
    "ΑΒ Βασιλόπουλος": "https://www.ab.gr/search/promotions",
}

PRODUCT_SELECTORS = [
    '[data-testid*="product"]',
    '[class*="product-card"]',
    '[class*="productCard"]',
    '[class*="ProductCard"]',
    '[class*="product-item"]',
    '[class*="productItem"]',
    'article',
    'li[class*="product"]',
    '[class*="product"]',
]

PRICE_PATTERN = re.compile(
    r"\d{1,4}(?:[.,]\d{1,2})?\s*€"
)

def clean_text(value):
    if not value:
        return ""
    return " ".join(value.split()).strip()

def normalize_price(value):
    if not value:
        return ""

    match = PRICE_PATTERN.search(value)
    if match:
        return clean_text(match.group(0))

    return ""

def get_image(element):
    image = element.locator("img").first

    try:
        if image.count():
            src = (
                image.get_attribute("src")
                or image.get_attribute("data-src")
                or image.get_attribute("data-lazy-src")
                or image.get_attribute("srcset")
            )

            if src:
                return src.split(",")[0].strip().split(" ")[0]

    except Exception:
        pass

    return ""

async def extract_products(page, supermarket):
    offers = []

    for selector in PRODUCT_SELECTORS:
        try:
            elements = page.locator(selector)
            count = await elements.count()

            if count == 0:
                continue

            print(f"  [DEBUG] Selector {selector}: {count} στοιχεία")

            for index in range(min(count, 500)):
                element = elements.nth(index)

                try:
                    text = clean_text(await element.inner_text(timeout=1500))

                    if len(text) < 5:
                        continue

                    price_match = PRICE_PATTERN.search(text)

                    if not price_match:
                        continue

                    price = normalize_price(price_match.group(0))

                    if not price:
                        continue

                    # Εντοπισμός τίτλου
                    title = ""

                    for title_selector in [
                        "h2",
                        "h3",
                        "h4",
                        '[class*="title"]',
                        '[class*="name"]',
                        "a",
                    ]:
                        title_element = element.locator(title_selector).first

                        if await title_element.count():
                            candidate = clean_text(
                                await title_element.inner_text(timeout=1000)
                            )

                            if candidate and len(candidate) > 3:
                                title = candidate
                                break

                    if not title:
                        lines = [
                            clean_text(line)
                            for line in text.split("\n")
                            if clean_text(line)
                        ]

                        title = next(
                            (
                                line for line in lines
                                if not PRICE_PATTERN.search(line)
                                and len(line) > 4
                            ),
                            ""
                        )

                    if not title:
                        continue

                    # Εντοπισμός παλιάς τιμής
                    old_price = ""

                    old_selectors = [
                        "del",
                        "s",
                        "strike",
                        '[class*="old-price"]',
                        '[class*="oldPrice"]',
                        '[class*="original-price"]',
                        '[class*="price-old"]',
                    ]

                    for old_selector in old_selectors:
                        old_element = element.locator(old_selector).first

                        if await old_element.count():
                            old_text = clean_text(
                                await old_element.inner_text(timeout=1000)
                            )

                            old_price = normalize_price(old_text)

                            if old_price and old_price != price:
                                break

                    # Εικόνα
                    image = await get_image(element)

                    # Αποφυγή διπλοεγγραφών
                    duplicate = any(
                        offer["supermarket"] == supermarket
                        and offer["title"].lower() == title.lower()
                        and offer["price"] == price
                        for offer in offers
                    )

                    if duplicate:
                        continue

                    offers.append({
                        "supermarket": supermarket,
                        "title": title,
                        "price": price,
                        "old_price": old_price,
                        "image": image,
                        "date": datetime.now().strftime("%d/%m/%Y"),
                    })

                except Exception:
                    continue

            # Αν βρέθηκαν προϊόντα, δεν χρειάζεται άλλος selector
            if offers:
                break

        except Exception as error:
            print(f"  [DEBUG] Selector error {selector}: {error}")

    return offers


async def scrape_supermarket(browser, supermarket, url):
    print(f"\n-> {supermarket}")

    offers = []

    page = await browser.new_page(
        viewport={"width": 1440, "height": 1000},
        locale="el-GR",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    )

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print(
            "  HTTP:",
            response.status if response else "χωρίς response"
        )
        print("  URL:", page.url)
        print("  TITLE:", await page.title())

        try:
            await page.locator("body").wait_for(timeout=15000)
            await page.wait_for_timeout(5000)
        except Exception:
            pass

        # Μικρή κύλιση για lazy-loaded προϊόντα
        for _ in range(4):
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(800)

        offers = await extract_products(page, supermarket)

        print(f"  [OK] {supermarket}: {len(offers)} προϊόντα")

        if not offers:
            body_text = await page.locator("body").inner_text()
            print("  [DEBUG] Κείμενο σελίδας:")
            print(body_text[:1200])

    except Exception as error:
        print(f"  [ERROR] {supermarket}: {error}")

    finally:
        await page.close()

    return offers


async def main():
    print("=== ΕΝΑΡΞΗ SCRAPER ===")

    all_offers = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        for supermarket, url in SUPERMARKETS.items():
            offers = await scrape_supermarket(
                browser,
                supermarket,
                url,
            )

            all_offers.extend(offers)

        await browser.close()

    # Αποφυγή διπλοεγγραφών
    unique_offers = []
    seen = set()

    for offer in all_offers:
        key = (
            offer["supermarket"],
            offer["title"].lower(),
            offer["price"],
        )

        if key not in seen:
            seen.add(key)
            unique_offers.append(offer)

    output = {
        "updated_at": datetime.now().isoformat(),
        "total": len(unique_offers),
        "offers": unique_offers,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== ΟΛΟΚΛΗΡΩΘΗΚΕ ===")
    print(f"Συνολικά προϊόντα: {len(unique_offers)}")
    print(f"Αποθηκεύτηκαν στο: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
