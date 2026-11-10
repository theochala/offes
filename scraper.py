import json
import os
from datetime import datetime
from ftplib import FTP
from playwright.sync_api import sync_playwright

# --- 1. Συναρτήσεις Scraping ανά Σούπερ Μάρκετ ---


def scrape_sklavenitis(page):
  print("Συλλογή προσφορών από Σκλαβενίτη...")
  offers = []
  try:
    # Παράδειγμα URL (άλλαξέ το με το πραγματικό link προσφορών)
    # page.goto("https://www.sklavenitis.gr/prosfores/", timeout=60000)
    # page.wait_for_selector(".product-item", timeout=10000)

    # Παράδειγμα εξαγωγής δεδομένων (απόδειξη λειτουργίας)
    offers.append({
        "supermarket": "Σκλαβενίτης",
        "title": "Παράδειγμα Προϊόντος Σκλαβενίτης",
        "price": "1.50€",
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
  except Exception as e:
    print(f"Σφάλμα στον Σκλαβενίτη: {e}")
  return offers


def scrape_ab(page):
  print("Συλλογή προσφορών από ΑΒ Βασιλόπουλο...")
  offers = []
  try:
    # page.goto("https://www.ab.gr/el/eshop/offers", timeout=60000)

    offers.append({
        "supermarket": "ΑΒ Βασιλόπουλος",
        "title": "Παράδειγμα Προϊόντος ΑΒ",
        "price": "2.10€",
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
  except Exception as e:
    print(f"Σφάλμα στον ΑΒ: {e}")
  return offers


def scrape_lidl(page):
  print("Συλλογή προσφορών από Lidl...")
  offers = []
  try:
    # page.goto("https://www.lidl.gr/c/ebdomadiaies-prosfores/s10007185", timeout=60000)

    offers.append({
        "supermarket": "Lidl",
        "title": "Παράδειγμα Προϊόντος Lidl",
        "price": "0.99€",
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
  except Exception as e:
    print(f"Σφάλμα στα Lidl: {e}")
  return offers


# --- 2. Κεντρική συνάρτηση που τα μαζεύει όλα ---


def scrape_all_supermarkets():
  print("Ξεκινάει το συνολικό scraping προσφορών...")
  all_offers = []

  with sync_playwright() as p:
    # Launch browser (headless=True για να τρέχει στο GitHub Actions)
    browser = p.chromium.launch(
        headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    page = browser.new_page()

    # User-agent για να μη μας κόβουν τα bot protections
    page.set_extra_http_headers({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    })

    # Καλλούμε τα scrapers για κάθε μάρκετ
    all_offers.extend(scrape_sklavenitis(page))
    all_offers.extend(scrape_ab(page))
    all_offers.extend(scrape_lidl(page))

    browser.close()

  # Δομή του JSON αρχείου
  data = {
      "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "total_offers": len(all_offers),
      "offers": all_offers,
  }

  filename = "clean_offers.json"
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

  print(
      f"Δημιουργήθηκε το {filename} με συνολικά {len(all_offers)} προσφορές."
  )
  return filename


# --- 3. Συνάρτηση αποστολής στο FTP (στο prosfores.infy.click/htdocs) ---


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

    # Πλοήγηση στον φάκελο prosfores.infy.click/htdocs
    ftp.cwd("prosfores.infy.click")
    ftp.cwd("htdocs")
    print(f"Τελικός φάκελος μεταφόρτωσης: {ftp.pwd()}")

    with open(filename, "rb") as f:
      ftp.storbinary(f"STOR {filename}", f)

    print(
        f"Το αρχείο {filename} ανέβηκε επιτυχώς στο prosfores.infy.click/htdocs!"
    )
    ftp.quit()
  except Exception as e:
    print(f"Αποτυχία μεταφόρτωσης στο FTP: {e}")


# --- 4. Εκτέλεση προγράμματος ---

if __name__ == "__main__":
  json_file = scrape_all_supermarkets()

  if json_file and os.path.exists(json_file):
    upload_to_ftp(json_file)
  else:
    print("Το αρχείο δεν βρέθηκε, η μεταφόρτωση παραλείπεται.")
