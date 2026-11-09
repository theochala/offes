import requests
from bs4 import BeautifulSoup
import json
import time

def get_e_katanalotis_promotions():
    """
    Παράδειγμα ανάκτησης προσφορών/τιμών από την επίσημη πλατφόρμα e-Katanalotis (API).
    Η πλατφόρμα συγκεντρώνει τιμές και προσφορές από τα μεγάλα σούπερ μάρκετ της Ελλάδας 
    (Σκλαβενίτης, ΑΒ Βασιλόπουλος, Μασούτης, Lidl, Κρητικός, κ.ά.).
    """
    url = "https://ekatanalotis.gov.gr/api/products" # Εικονικό/Ενδεικτικό endpoint
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    print("Αναζήτηση προσφορών...")
    # Εδώ γίνεται η κλήση στο API ή η σάρωση (scraping) της σελίδας
    # response = requests.get(url, headers=headers)
    # data = response.json()
    
    # Ενδεικτικά δεδομένα δομής
    promotions = [
        {
            "supermarket": "Σκλαβενίτης",
            "product": "Γάλα Φρέσκο 1L",
            "original_price": 1.65,
            "offer_price": 1.35,
            "discount": "-18%"
        },
        {
            "supermarket": "ΑΒ Βασιλόπουλος",
            "product": "Ελαιόλαδο Extra Παρθένο 1L",
            "original_price": 11.50,
            "offer_price": 8.90,
            "discount": "-22%"
        },
        {
            "supermarket": "Μασούτης",
            "product": "Καφέ Ελληνικό 200g",
            "original_price": 3.80,
            "offer_price": 2.95,
            "discount": "-22%"
        }
    ]
    
    return promotions

def save_to_json(data, filename="supermarket_offers.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Τα δεδομένα αποθηκεύτηκαν στο {filename}")

if __name__ == "__main__":
    offers = get_e_katanalotis_promotions()
    for offer in offers:
        print(f"[{offer['supermarket']}] {offer['product']}: Από {offer['original_price']}€ -> {offer['offer_price']}€ ({offer['discount']})")
    save_to_json(offers)
