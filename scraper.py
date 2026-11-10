import json
import os
from datetime import datetime
from ftplib import FTP
from playwright.sync_api import sync_playwright

# Σύνδεσμοι Προσφορών Σούπερ Μάρκετ
TARGET_URLS = {
    "Μασούτης": "https://www.masoutis.gr/offers",
    "Σκλαβενίτης": "https://www.sklavenitis.gr/sylloges/prosfores/",
    "Lidl": (
        "https://www.lidl-hellas.gr/c/store/evdomadiaies-epiloges-26kw45/a10106403"
    ),
    "MyMarket": (
        "https://www.mymarket.gr/offers?srsltid=AYCX9vJAEuUd6A9J70LsUgVl9eSugbCgIdwLfjS928We_Oc2AeBL0hoP"
    ),
    "ΑΒ Βασιλόπουλος": "https://www.ab.gr/search/promotions",
}


def scrape_all_supermarkets():
  print("Ξεκινάει η συλλογή πραγματικών προϊόντων από τα links...")
  all_offers = []

  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()

    for market_name, url in TARGET_URLS.items():
      print(f"-> Σάρωση σελίδας {market_name}: {url}")
      try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(
            4000
        )  # Αναμονή για να φορτώσει η δυναμική JavaScript

        market_offers = []

        # Δοκιμή εύρεσης προϊόντων με κοινούς selectors e-shop (κάρτες προϊόντων)
        # Αναζητούμε στοιχεία που ταιριάζουν σε τίτλους και τιμές προϊόντων
        product_cards = page.locator(
            ".product-item, .item-card, article, [data-product-id]"
        ).all()

        if product_cards:
          for card in product_cards:
            try:
              # Προσπάθεια εξαγωγής τίτλου
              title_el = card.locator(
                  "h2, h3, .product-title, .title, a"
              ).first.inner_text()
              # Προσπάθεια εξαγωγής τιμής
              price_el = card.locator(
                  ".price, .current-price, .value, span"
              ).first.inner_text()

              clean_title = title_el.strip() if title_el else ""
              clean_price = price_el.strip() if price_el else ""

              if len(clean_title) > 2 and any(
                  char.isdigit() for char in clean_price
              ):
                market_offers.append({
                    "supermarket": market_name,
                    "title": clean_title,
                    "price": clean_price,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                })
            except:
              continue

        # Αν οι ειδικές κάρτες δεν απέδωσαν, παίρνουμε γενικούς τίτλους κειμένου από τη σελίδα προσφορών
        if not market_offers:
          titles = page.locator(
              "h2, h3, h4, span.title, a.title"
          ).all_inner_texts()
          for t in titles:
            t_clean = t.strip()
            if (
                len(t_clean) > 5
                and t_clean not in [o["title"] for o in market_offers]
                and not any(
                    word in t_clean.lower()
                    for word in ["καλάθι", "σούπερ", "αρχική", "σύνδεση"]
                )
            ):
              market_offers.append({
                  "supermarket": market_name,
                  "title": t_clean,
                  "price": "Δείτε το site",
                  "date": datetime.now().strftime("%Y-%m-%d"),
              })

        if market_offers:
          all_offers.extend(market_offers)
          print(
              f"  [+] Βρέθηκαν {len(market_offers)} προϊόντα για"
              f" {market_name}."
          )
        else:
          print(
              f"  [!] Δεν εντοπίστηκαν ανοιχτά προϊόντα στο {market_name}"
              " (πιθανή προστασία bot)."
          )

      except Exception as e:
        print(f"  [X] Σφάλμα φόρτωσης στο {market_name}: {e}")

    browser.close()

  # ΔΕΝ προσθέτουμε ψεύτικα δεδομένα αν είναι κενή η λίστα. Θα γράφει ακριβώς ό,τι βρήκε.
  data = {
      "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "total_offers": len(all_offers),
      "offers": all_offers,
  }

  filename = "clean_offers.json"
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

  print(
      f"Δημιουργήθηκε το {filename} με συνολικά {len(all_offers)} πραγματικά"
      " προϊόντα."
  )
  return filename


def upload_all_to_ftp():
  ftp_server = os.getenv("FTP_SERVER")
  ftp_user = os.getenv("FTP_USERNAME")
  ftp_pass = os.getenv("FTP_PASSWORD")

  if not all([ftp_server, ftp_user, ftp_pass]):
    print("Σφάλμα: Λείπουν τα στοιχεία FTP.")
    return

  print(f"Σύνδεση στο FTP: {ftp_server}...")
  try:
    ftp = FTP(ftp_server)
    ftp.login(user=ftp_user, passwd=ftp_pass)

    ftp.cwd("prosfores.infy.click")
    ftp.cwd("htdocs")

    for filename in os.listdir("."):
      if os.path.isfile(filename) and not filename.startswith("."):
        if filename == "scraper.py":
          continue

        with open(filename, "rb") as f:
          ftp.storbinary(f"STOR {filename}", f)
        print(f"Ανέβηκε στο FTP: {filename}")

    ftp.quit()
    print("Η μεταφόρτωση ολοκληρώθηκε!")
  except Exception as e:
    print(f"Σφάλμα FTP: {e}")


if __name__ == "__main__":
  scrape_all_supermarkets()
  upload_all_to_ftp()
