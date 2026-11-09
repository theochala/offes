import json
import time
import os
import ftplib
from playwright.sync_api import sync_playwright

TARGET_SOURCES = {
    "KRITIKOS": "https://kritikos-sm.gr/prosfores/",
    "SKLEVENITIS": "https://www.sklavenitis.gr/prosfores/",
    "AB_VASSILOPOULOS": "https://www.ab.gr/promotions",
    "MASOUTIS": "https://www.masoutis.gr/offers",
    "LIDL": "https://www.lidl-hellas.gr/c/prosfores/a100000"
}

def scrape_supermarket(page, url, supermarket_name):
    offers = []
    try:
        print(f"   [Playwright] Άνοιγμα σελίδας για {supermarket_name}: {url}")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        time.sleep(3)
        
        cards = page.locator("article, div[class*='product'], div[class*='offer'], li[class*='product']").all()
        print(f"   [Playwright] Βρέθηκαν {len(cards)} πιθανές κάρτες προϊόντων στο {supermarket_name}.")

        for card in cards:
            try:
                # Αναζήτηση τίτλου
                title_elem = card.locator("h2, h3, h4, a[class*='title'], div[class*='title']").first
                title = title_elem.inner_text(timeout=200).strip() if title_elem.count() > 0 else ""

                # Αναζήτηση τιμής προσφοράς
                price_elem = card.locator("span[class*='price'], div[class*='price'], span[class*='amount']").first
                price = price_elem.inner_text(timeout=200).strip() if price_elem.count() > 0 else ""

                # Αναζήτηση παλιάς/αρχικής τιμής (δείχνει ότι είναι όντως προσφορά)
                orig_price_elem = card.locator("span[class*='old'], span[class*='original'], del, span[class*='line-through']").first
                orig_price = orig_price_elem.inner_text(timeout=200).strip() if orig_price_elem.count() > 0 else "—"

                # Έλεγχος ετικέτας προσφοράς / ποσοστού έκπτωσης
                badge_elem = card.locator("div[class*='badge'], span[class*='discount'], div[class*='tag']").first
                badge_text = badge_elem.inner_text(timeout=200).strip() if badge_elem.count() > 0 else ""

                # Αυστηρό φίλτρο: Κρατάμε μόνο προϊόντα με τίτλο, τιμή και ένδειξη προσφοράς (αρχική τιμή ή ποσοστό έκπτωσης)
                if title and price and (orig_price != "—" or "%" in badge_text or "προσφορά" in badge_text.lower() or "προσφορα" in title.lower()):
                    img_elem = card.locator("img").first
                    img_url = "https://via.placeholder.com/150"
                    if img_elem.count() > 0:
                        src = img_elem.get_attribute("src") or img_elem.get_attribute("data-src")
                        if src:
                            img_url = "https:" + src if src.startswith("//") else src

                    offers.append({
                        "supermarket": supermarket_name,
                        "image_url": img_url,
                        "product_title": title,
                        "offer_price": price,
                        "unit_or_original_price": orig_price,
                        "source_link": url
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"   [Προειδοποίηση] Σφάλμα στο {supermarket_name}: {e}")

    # Fallback: Αν δεν βρει αυστηρές προσφορές, παίρνει λίγα διαθέσιμα για να μην μείνει κενό
    if not offers:
        print(f"   [Info] Δεν βρέθηκαν αυστηρές προσφορές με φίλτρο στο {supermarket_name}, λήψη γενικών προϊόντων...")
        try:
            for card in cards[:5]:
                title_elem = card.locator("h2, h3, h4, a[class*='title'], div[class*='title']").first
                title = title_elem.inner_text(timeout=200).strip() if title_elem.count() > 0 else f"Προϊόν {supermarket_name}"
                price_elem = card.locator("span[class*='price'], div[class*='price'], span[class*='amount']").first
                price = price_elem.inner_text(timeout=200).strip() if price_elem.count() > 0 else "0.00 €"
                
                offers.append({
                    "supermarket": supermarket_name,
                    "image_url": "https://via.placeholder.com/150",
                    "product_title": title,
                    "offer_price": price,
                    "unit_or_original_price": "—",
                    "source_link": url
                })
        except Exception:
            pass

    return offers

def upload_via_ftp(filename):
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not ftp_server or not ftp_user or not ftp_pass:
        print("❌ Σφάλμα: Τα FTP secrets δεν βρέθηκαν στο περιβάλλον!")
        return

    try:
        print(f"📡 Σύνδεση στο FTP server: {ftp_server}...")
        with ftplib.FTP(ftp_server, timeout=30) as ftp:
            ftp.login(ftp_user, ftp_pass)
            print("✅ Επιτυχής σύνδεση FTP!")
            
            # Δοκιμή φακέλων για το InfinityFree
            folders_to_try = ["htdocs", "public_html", "."]
            uploaded = False
            for folder in folders_to_try:
                try:
                    ftp.cwd(folder)
                    print(f"📁 Μετάβαση στον φάκελο: {folder}")
                    with open(filename, "rb") as f:
                        ftp.storbinary(f"STOR {filename}", f)
                    print(f"🚀 Το αρχείο {filename} ανέβηκε επιτυχώς στον φάκελο {folder}!")
                    uploaded = True
                    break
                except Exception:
                    try:
                        ftp.cwd("/")
                    except:
                        pass
            
            if not uploaded:
                with open(filename, "rb") as f:
                    ftp.storbinary(f"STOR {filename}", f)
                print(f"🚀 Το αρχείο {filename} ανέβηκε στο root!")

    except Exception as e:
        print(f"❌ Κρίσιμο σφάλμα κατά το FTP upload: {e}")

def main():
    store_offers = {}

    print("Ξεκινάει η συλλογή προσφορών ανά μάρκετ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        page = context.new_page()

        for name, link in TARGET_SOURCES.items():
            store_offers[name] = scrape_supermarket(page, link, name)

        browser.close()

    # Round-robin ανάμιξη: 1 προϊόν από κάθε μάρκετ εναλλάξ
    interleaved_offers = []
    max_len = max(len(lst) for lst in store_offers.values()) if store_offers else 0

    for i in range(max_len):
        for name in TARGET_SOURCES.keys():
            if i < len(store_offers[name]):
                interleaved_offers.append(store_offers[name][i])

    output_filename = "clean_offers.json"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(interleaved_offers, f, ensure_ascii=False, indent=4)
        print(f"\nΕπιτυχία! Αποθηκεύτηκαν συνολικά {len(interleaved_offers)} προσφορές εναλλάξ στο '{output_filename}'.")
        
        # Αυτόνομη αποστολή μέσω FTP στον InfinityFree
        upload_via_ftp(output_filename)

    except Exception as e:
        print(f"Σφάλμα αποθήκευσης αρχείου: {e}")
        exit(1)

if __name__ == "__main__":
    main()
