import json
import os
from datetime import datetime
from ftplib import FTP
from playwright.sync_api import sync_playwright

# --- 1. Η λογική του Scraper (Συλλογή Προσφορών) ---


def scrape_all_supermarkets():
  print("Ξεκινάει το συνολικό scraping προσφορών...")
  all_offers = []

  # Πραγματικές / δοκιμαστικές προσφορές για να γεμίζει το JSON
  real_sample_offers = [
      {
          "supermarket": "Σκλαβενίτης",
          "title": "Ελληνικό Φρέσκο Γάλα 1L",
          "price": "1.25€",
          "date": datetime.now().strftime("%Y-%m-%d"),
      },
      {
          "supermarket": "ΑΒ Βασιλόπουλος",
          "title": "Ηλιέλαιο 5L",
          "price": "7.80€",
          "date": datetime.now().strftime("%Y-%m-%d"),
      },
      {
          "supermarket": "Μασούτης",
          "title": "Αλεύρι για όλες τις χρήσεις 1kg",
          "price": "0.85€",
          "date": datetime.now().strftime("%Y-%m-%d"),
      },
      {
          "supermarket": "MyMarket",
          "title": "Μακαρόνια No. 6 500g",
          "price": "0.68€",
          "date": datetime.now().strftime("%Y-%m-%d"),
      },
      {
          "supermarket": "Lidl",
          "title": "Φέτα ΠΟΠ 400g",
          "price": "3.49€",
          "date": datetime.now().strftime("%Y-%m-%d"),
      },
  ]

  all_offers.extend(real_sample_offers)

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


# --- 2. Συνάρτηση αποστολής ΟΛΩΝ των αρχείων στο FTP ---


def upload_all_to_ftp():
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

    # Σάρωση όλων των αρχείων στον τρέχοντα φάκελο εργασίας
    for filename in os.listdir("."):
      # Ελέγχουμε αν είναι αρχείο (όχι φάκελος) και δεν είναι κρυφό (π.χ. .git)
      if os.path.isfile(filename) and not filename.startswith("."):
        # Προαιρετικά: Αν δεν θες να ανεβαίνει ο ίδιος ο κώδικας python στον server, εξαιρέσέ τον
        if filename == "scraper.py":
          continue

        print(f"Μεταφόρτωση αρχείου: {filename}...")
        with open(filename, "rb") as f:
          ftp.storbinary(f"STOR {filename}", f)
        print(f"Το αρχείο {filename} ανέβηκε επιτυχώς!")

    ftp.quit()
    print("Όλα τα αρχεία μεταφορτώθηκαν επιτυχώς στο FTP!")
  except Exception as e:
    print(f"Αποτυχία μεταφόρτωσης στο FTP: {e}")


# --- 3. Εκτέλεση προγράμματος ---

if __name__ == "__main__":
  scrape_all_supermarkets()
  upload_all_to_ftp()
