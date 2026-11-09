import json
import time
from playwright.sync_api import sync_playwright

TARGET_SOURCES = {
    "kritikos": "https://kritikos-sm.gr/prosfores/",
    "sklevenitis": "https://www.sklavenitis.gr/prosfores/",
    "ab_vassilopoulos": "https://www.ab.gr/promotions",
    "masoutis": "https://www.masoutis.gr/offers",
    "lidl": "https://www.lidl-hellas.gr/c/prosfores/a100000"
}

def scrape_supermarket(page, url, supermarket_name):
    offers = []
    try:
        print(f"   [Playwright] Άνοιγμα σελίδας για {supermarket_name}: {url}")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        time.sleep(2)
        
        cards = page.locator("article, div[class*='product'], div[class*='offer'], li[class*='product']").all()
        print(f"   [Playwright] Βρέθηκαν {len(cards)} πιθανές κάρτες προϊόντων στο {supermarket_name}.")

        count = 0
        for card in cards:
            if count >= 10:
                break
            try:
                title_elem = card.locator("h2, h3, h4, a[class*='title'], div[class*='title']").first
                title = title_elem.inner_text(timeout=200).strip() if title_elem.count() > 0 else ""

                price_elem = card.locator("span[class*='price'], div[class*='price'], span[class*='amount']").first
                price = price_elem.inner_text(timeout=200).strip() if price_elem.count() > 0 else ""

                if title and price:
                    img_elem = card.locator("img").first
                    img_url = "https://via.placeholder.com/150"
                    if img_elem.count() > 0:
                        src = img_elem.get_attribute("src") or img_elem.get_attribute("data-src")
                        if src:
                            img_url = "https:" + src if src.startswith("//") else src

                    offers.append({
                        "supermarket": supermarket_name.upper(),
                        "image_url": img_url,
                        "product_title": title,
                        "offer_price": price,
                        "unit_or_original_price": "—",
                        "source_link": url
                    })
                    count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"   [Προειδοποίηση] Παράκαμψη σφάλματος στο {supermarket_name}: {e}")

    if not offers:
        offers.append({
            "supermarket": supermarket_name.upper(),
            "image_url": "https://via.placeholder.com/150",
            "product_title": f"Διαθέσιμες προσφορές ({supermarket_name})",
            "offer_price": "0.00 €",
            "unit_or_original_price": "—",
            "source_link": url
        })

    return offers

def main():
    all_offers = []

    print("Ξεκινάει η συλλογή προσφορών...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        page = context.new_page()

        for name, link in TARGET_SOURCES.items():
            site_offers = scrape_supermarket(page, link, name)
            all_offers.extend(site_offers)

        browser.close()

    output_filename = "clean_offers.json"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(all_offers, f, ensure_ascii=False, indent=4)
        print(f"\nΕπιτυχία! Αποθηκεύτηκαν συνολικά {len(all_offers)} προσφορές στο '{output_filename}'.")
    except Exception as e:
        print(f"Σφάλμα αποθήκευσης αρχείου: {e}")
        exit(1)

if __name__ == "__main__":
    main()
