import json
import os
from ftplib import FTP
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- 1. Η λογική του Scraper ---

def scrape_supermarket_offers():
    print("Ξεκινάει το scraping των προσφορών...")
    
    # Παράδειγμα χρήσης Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # page.goto("https://example-supermarket.gr/offers")
        browser.close()

    # Δεδομένα προσφορών
    sample_data = {
        "updated_at": "2026-06-06",
        "offers": [
            {"title": "Παράδειγμα Προϊόντος", "price": "1.99€"}
        ]
    }

    filename = "clean_offers.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=4)

    print(f"Το αρχείο {filename} δημιουργήθηκε επιτυχώς.")
    return filename

# --- 2. Η συνάρτηση αποστολής στο FTP (μέσα στο prosfores.infy.click/htdocs) ---

def upload_to_ftp(filename="clean_offers.json"):
    ftp_server = os.getenv("FTP_SERVER")
    ftp_user = os.getenv("FTP_USERNAME")
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("Σφάλμα: Τα στοιχεία FTP δεν βρέθηκαν στις μεταβλητές περιβάλλοντος.")
        return

    print(f"Σύνδεση στον FTP server: {ftp_server}...")
    try:
        ftp = FTP(ftp_server)
        ftp.login(user=ftp_user, passwd=ftp_pass)

        # 1. Μπαίνουμε στον φάκελο του domain
        ftp.cwd("prosfores.infy.click")
        print(f"Μπήκαμε στον φάκελο: {ftp.pwd()}")

        # 2. Μπαίνουμε στον υποφάκελο htdocs
        ftp.cwd("htdocs")
        print(f"Τελικός φάκελος μεταφόρτωσης: {ftp.pwd()}")

        # 3. Ανεβάζουμε το αρχείο
        with open(filename, "rb") as f:
            ftp.storbinary(f"STOR {filename}", f)

        print(f"Το αρχείο {filename} ανέβηκε επιτυχώς στο prosfores.infy.click/htdocs!")
        ftp.quit()
    except Exception as e:
        print(f"Αποτυχία μεταφόρτωσης στο FTP: {e}")

# --- 3. Εκτέλεση ---

if __name__ == "__main__":
    json_file = scrape_supermarket_offers()
    
    if json_file and os.path.exists(json_file):
        upload_to_ftp(json_file)
    else:
        print("Το αρχείο δεν βρέθηκε, η μεταφόρτωση παραλείπεται.")
