import json
import urllib.request
import urllib.error

TARGET_SOURCES = {
    "e_katanalotis_api": "https://e-katanalotis.gov.gr/api/products",
    "sklevenitis": "https://www.sklavenitis.gr/prosfores/",
    "ab_vassilopoulos": "https://www.ab.gr/promotions",
    "masoutis": "https://www.masoutis.gr/offers",
    "lidl": "https://www.lidl-hellas.gr/c/prosfores/a100000",
    "kritikos": "https://kritikos-sm.gr/prosfores/"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "el-GR,el;q=0.9,en;q=0.8"
}

def safe_fetch(url):
    """Ασφαλής λήψη δεδομένων χωρίς να διακόπτεται η εκτέλεση σε περίπτωση σφάλματος"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Προειδοποίηση: Αποτυχία σύνδεσης στο {url} -> {e}")
        return None

def main():
    all_offers = []

    print("Ξεκινάει η συλλογή δεδομένων...")
    
    # 1. e-Katanalotis API
    api_data = safe_fetch(TARGET_SOURCES["e_katanalotis_api"])
    if api_data:
        try:
            data = json.loads(api_data)
            items = data.get("products", data if isinstance(data, list) else [])
            for item in items[:15]:
                all_offers.append({
                    "supermarket": item.get("supermarket", "ΚΡΗΤΙΚΟΣ").upper(),
                    "image_url": item.get("image", "https://via.placeholder.com/150"),
                    "product_title": f"{item.get('category', 'Προσφορές')} | {item.get('name', 'Προϊόν')}",
                    "offer_price": f"{item.get('offer_price', 0.0):.2f} €",
                    "unit_or_original_price": f"{item.get('price', 0.0):.2f} €",
                    "source_link": TARGET_SOURCES["e_katanalotis_api"]
                })
        except Exception as e:
            print(fσ"Σφάλμα επεξεργασίας JSON: {e}")

    # 2. Υπόλοιπα supermarkets (Fallback cards αν μπλοκαριστούν)
    for name, link in TARGET_SOURCES.items():
        if name == "e_katanalotis_api":
            continue
            
        html = safe_fetch(link)
        status = "Επιτυχής πρόσβαση" if html else "Προσωρινός αποκλεισμός / Error"
        
        all_offers.append({
            "supermarket": name.upper(),
            "image_url": "https://via.placeholder.com/150",
            "product_title": f"Κατάσταση Σάρωσης: {status}",
            "offer_price": "0.00 €",
            "unit_or_original_price": "—",
            "source_link": link
        })

    # Αποθήκευση στο clean_offers.json
    try:
        with open("clean_offers.json", "w", encoding="utf-8") as f:
            json.dump(all_offers, f, ensure_ascii=False, indent=4)
        print("Επιτυχής αποθήκευση στο clean_offers.json!")
    except Exception as e:
        print(f"Σφάλμα αποθήκευσης αρχείου: {e}")

if __name__ == "__main__":
    main()
