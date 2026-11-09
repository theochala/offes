import json
import re
import requests
from bs4 import BeautifulSoup

# 1. Πηγές και Links Προσφορών / APIs
TARGET_SOURCES = {
    "e_katanalotis_api": "https://e-katanalotis.gov.gr/api/products",
    "sklevenitis": "https://www.sklavenitis.gr/prosfores/",
    "ab_vassilopoulos": "https://www.ab.gr/promotions",
    "masoutis": "https://www.masoutis.gr/offers",
    "lidl": "https://www.lidl-hellas.gr/c/prosfores/a100000",
    "kritikos": "https://kritikos-sm.gr/prosfores/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "el-GR,el;q=0.9,en;q=0.8",
}


def fetch_e_katanalotis_data():
    """Ανάκτηση ζωντανών δεδομένων από το API του e-Καταναλωτής."""
    offers = []
    url = TARGET_SOURCES["e_katanalotis_api"]
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Προσαρμογή ανάλογα με τη δομή του JSON του API
            items = data.get("products", data if isinstance(data, list) else [])
            for item in items[:20]:  # Παράδειγμα για τα πρώτα 20 προϊόντα
                offers.append(
                    {
                        "supermarket": item.get("supermarket", "e-Katanalotis"),
                        "product": item.get("name") or item.get("title"),
                        "original_price": item.get("price"),
                        "offer_price": item.get("offer_price"),
                        "discount": item.get("discount"),
                        "source_link": "https://e-katanalotis.gov.gr/",
                    }
                )
    except Exception as e:
        print(f"Σφάλμα κατά την ανάκτηση από e-Καταναλωτή: {e}")

    return offers


def fetch_generic_offers(supermarket_name, url):
    """Scraper για ανάκτηση προσφορών απευθείας από τις σελίδες των σούπερ μάρκετ."""
    offers = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")

            # Εντοπισμός στοιχείων με λέξεις-κλειδιά στις κλάσεις ή στο κείμενο
            cards = soup.find_all(
                ["div", "article", "li"], class_=re.compile(r"product|offer|item", re.I)
            )

            for card in cards[:10]:
                title_elem = card.find(["h2", "h3", "h4", "span", "a"])
                price_elem = card.find(class_=re.compile(r"price|amount", re.I))

                if title_elem and price_elem:
                    offers.append(
                        {
                            "supermarket": supermarket_name,
                            "product": title_elem.text.strip(),
                            "original_price": None,
                            "offer_price": price_elem.text.strip(),
                            "discount": None,
                            "source_link": url,
                        }
                    )
    except Exception as e:
        print(f"Σφάλμα κατά την άντληση από {supermarket_name}: {e}")

    return offers


def main():
    all_offers = []

    print("1. Συλλογή προσφορών από e-Καταναλωτή...")
    api_offers = fetch_e_katanalotis_data()
    all_offers.extend(api_offers)

    print("2. Σάρωση ιστοσελίδων σούπερ μάρκετ...")
    for name, link in TARGET_SOURCES.items():
        if name == "e_katanalotis_api":
            continue
        print(f"   - Άντληση από {name} ({link})...")
        site_offers = fetch_generic_offers(name, link)
        all_offers.extend(site_offers)

    # Αποθήκευση στο clean_offers.json
    output_filename = "clean_offers.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_offers, f, ensure_ascii=False, indent=4)

    print(f"\nΗ διαδικασία ολοκληρώθηκε! Αποθηκεύτηκαν {len(all_offers)} προσφορές στο '{output_filename}'.")


if __name__ == "__main__":
    main()
