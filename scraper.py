import json
import os
import re
from datetime import datetime
from ftplib import FTP
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

TARGET_URLS = {
    "Μασούτης": "https://www.masoutis.gr/offers",
    "Σκλαβενίτης": "https://www.sklavenitis.gr/sylloges/prosfores/",
    "Lidl": "https://www.lidl-hellas.gr/c/store/evdomadiaies-epiloges-26kw45/a10106403",
    "MyMarket": "https://www.mymarket.gr/offers",
    "ΑΒ Βασιλόπουλος": "https://www.ab.gr/search/promotions"
}

def parse_html_products(html_content, market_name):
    soup = BeautifulSoup(html_content, 'html.parser')
    offers = []

    # Εντοπισμός όλων των πιθανών containers προϊόντων
    cards = soup.select("article, div[class*='product'], div[class*='card'], div[class*='item'], li[class*='product']")

    for card in cards[:150]:
        try:
            # 1. Εξαγωγή Εικόνας
            img_tag = card.find("img")
            img_src = ""
            if img_tag:
                img_src = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("srcset", "").split(" ")[0]
                if img_src and not img_src.startswith("http"):
                    if img_src.startswith("//"):
                        img_src = "https:" + img_src
                    else:
                        img_src = ""

            # 2. Συλλογή Κειμένων
            texts = [t.strip() for t in card.stripped_strings if len(t.strip()) > 0]
            if not texts:
                continue

            price_text = ""
            title_text = ""
            possible_titles = []

            for txt in texts:
                # Εντοπισμός Τιμής (περιέχει αριθμό και € ή κόμμα/τελεία σε μικρό μήκος)
                if any(char.isdigit() for char in txt) and ('€' in txt or ',' in txt or '.' in txt) and len(txt) <= 10:
                    if not price_text and re.search(r'\d', txt):
                        price_text = txt
                # Εντοπισμός Τίτλου
                elif len(txt) > 3 and not any(w in txt.lower() for w in [
                    "καλάθι", "σούπερ", "αρχική", "σύνδεση", "προσφορές", "cookies", 
                    "newsletter", "εγγραφή", "αποδοχή", "απόρριψη", "λεπτομέρειες"
                ]):
                    possible_titles.append(txt)

            if possible_titles:
                title_text = max(possible_titles, key=len)

            if title_text and price_text:
                # Αποφυγή διπλότυπων τίτλων
                if not any(o['title'] == title_text for o in offers):
                    offers.append({
                        "supermarket": market_name,
                        "title": title_text,
                        "price": price_text,
                        "old_price": "",
                        "image": img_src if img_src else "https://via.placeholder.com/150?text=Offer",
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
        except Exception:
            continue

    return offers

def scrape_all_supermarkets():
    print("=== ΕΝΑΡΞΗ SCRAPER ===")
    all_offers = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="el-GR",
            timezone_id="Europe/Athens"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = context.new_page()

        for market_name, url in TARGET_URLS.items():
            print(f"\n-> {market_name}: {url}")
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                status = response.status if response else 0
                print(f"  HTTP Status: {status}")

                if status == 403 and market_name == "Σκλαβενίτης":
                    # Fallback URL για Σκλαβενίτη σε περίπτωση 403 block
                    alt_url = "https://www.sklavenitis.gr/prosfores/"
                    print(f"  [Retry] Δοκιμή εναλλακτικού URL: {alt_url}")
                    page.goto(alt_url, wait_until="domcontentloaded", timeout=30000)

                page.wait_for_timeout(2000)

                # Αυτόματο κλείσιμο παραθύρων cookies
                try:
                    cookie_btn = page.locator("button:has-text('Αποδοχή'), button:has-text('Συμφωνώ'), #onetrust-accept-btn-handler").first
                    if cookie_btn.count() > 0:
                        cookie_btn.click(timeout=2000)
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Scroll για ενεργοποίηση lazy loading
                for _ in range(5):
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(1000)

                # Λήψη του πλήρως rendered HTML
                html_content = page.content()
                market_offers = parse_html_products(html_content, market_name)

                if market_offers:
                    all_offers.extend(market_offers)
                    print(f"  [OK] {market_name}: Εξήχθησαν {len(market_offers)} πραγματικά προϊόντα.")
                else:
                    print(f"  [!] {market_name}: 0 προϊόντα.")

            except Exception as ex:
                print(f"  [X] Σφάλμα στο {market_name}: {ex}")
                continue

        browser.close()

    # Εγγραφή στο JSON
    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_offers": len(all_offers),
        "offers": all_offers
    }

    filename = "clean_offers.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"\n=== ΟΛΟΚΛΗΡΩΘΗΚΕ ===")
    print(f"Συνολικά πραγματικά προϊόντα: {len(all_offers)}")
    return filename

def upload_all_to_ftp():
    print("\n=== ΜΕΤΑΦΟΡΤΩΣΗ FTP ===")
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("Σφάλμα: Λείπουν τα στοιχεία FTP από τα GitHub Secrets.")
        return

    try:
        ftp = FTP(ftp_server, timeout=10)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        ftp.cwd("prosfores.infy.click")
        ftp.cwd("htdocs")

        for filename in os.listdir("."):
            if os.path.isfile(filename) and not filename.startswith("."):
                if filename == "scraper.py":
                    continue
                with open(filename, "rb") as f:
                    ftp.storbinary(f"STOR {filename}", f)
                print(f"Ανέβηκε: {filename}")

        ftp.quit()
        print("Επιτυχής ολοκλήρωση FTP!")
    except Exception as e:
        print(f"[X] Σφάλμα FTP: {e}")

if __name__ == "__main__":
    json_file = scrape_all_supermarkets()
    upload_all_to_ftp()
