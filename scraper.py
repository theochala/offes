import json
import os
from ftplib import FTP
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- 1. Η λογική του Scraper (Παράδειγμα) ---


def scrape_supermarket_offers():
  print("Ξεκινάει το scraping των προσφορών...")

  offers = []

  # Παράδειγμα χρήσης Playwright (όπως δηλώνεις στο workflow)
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Παράδειγμα URL (άλλαξέ το με αυτό που θες)
    # page.goto("https://example-supermarket.gr/offers")
    # html = page.content()

    browser.close()

  # Εδώ αποθηκεύεις τα δεδομένα σου στο clean_offers.json
  # (Για δοκιμή δημιουργούμε ένα απλό αρχείο)
  sample_data = {
      "updated_at": "2026-06-06",
      "offers": [{"title": "Παράδειγμα Προϊόντος", "price": "1.99€"}],
  }

  filename = "clean_offers.json"
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(sample_data, f, ensure_ascii=False, indent=4)

  print(f"Το αρχείο {filename} δημιουργήθηκε επιτυχώς.")
  return filename


# --- 2. Η συνάρτηση αποστολής στο FTP ---


def upload_to_ftp(filename="clean_offers.json"):
  ftp_server = os.getenv("FTP_SERVER")
  ftp_user = os.getenv("FTP_USERNAME")
  ftp_pass = os.getenv("FTP_PASSWORD")

  if not all([ftp_server, ftp_user, ftp_pass]):
    print(
        "Σφάλμα: Τα στοιχεία FTP (SERVER, USERNAME, PASSWORD) δεν βρέθηκαν στις"
        " μεταβλητές περιβάλλοντος."
    )
    return

  print(f"Σύνδεση στον FTP server: {ftp_server}...")
  try:
    ftp = FTP(ftp_server)
    ftp.login(user=ftp_user, passwd=ftp_pass)

    with open(filename, "rb") as f:
      # Ανεβάζει το αρχείο στο root του FTP.
      # Αν θες να το βάλεις σε φάκελο, γράψ' το π.χ. 'public_html/clean_offers.json'
      ftp.storbinary(f"STOR {filename}", f)

    print(f"Το αρχείο {filename} ανέβηκε επιτυχώς στο FTP server!")
    ftp.quit()
  except Exception as e:
    print(f"Αποτυχία μεταφόρτωσης στο FTP: {e}")


# --- 3. Εκτέλεση ---

if __name__ == "__main__":
  # 1. Τρέχει το scraping και φτιάχνει το αρχείο
  json_file = scrape_supermarket_offers()

  # 2. Ανέβασμα στο FTP
  if json_file and os.path.exists(json_file):
    upload_to_ftp(json_file)
  else:
    print("Το αρχείο δεν βρέθηκε, η μεταφόρτωση στο FTP παραλείπεται.")
