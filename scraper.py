import json
import urllib.request
import urllib.error

# Ορισμός πηγών
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

def fetch_url_safely(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"   [Σφάλμα σύνδεσης] {url}: {e}")
    return None

def main():
    all_offers = []

    print("1. Συλλογή προσφορών και διαμόρφωση σε μορφή καρτέλας...")
    api_url = TARGET_SOURCES["e_katanalotis_api"]
    api_data = fetch_url_safely(api_url)
    
    if api_data:
        try:
            data = json.loads(api_data)
            items = data.get("products", data if isinstance(data, list) else [])
            for item in items[:20]:
                # Δομή αντίστοιχη με τις κάρτες της εικόνας
                card_item = {
                    "supermarket": item.get("supermarket", "ΚΡΗΤΙΚΟΣ").upper(),
                    "image_url": item.get("image", "https://via.placeholder.com/150"),
                    "product_title": f"{item.get('category', 'Προϊόντα')} | {item.get('name', 'Άγνωστο Προϊόν')}",
                    "offer_price": f"{item.get('offer_price', 0.0):.2f} €" if item.get('offer_price') else "0.00 €",
                    "unit_or_original_price": f"{item.get('price', 0.0):.2f} €" if item.get('price') else "—",
                    "source_link": api_url
                }
                all_offers.append(card_item)
        except json.JSONDecodeError:
            print("   [Σφάλμα] Τα δεδομένα του API δεν είχαν μορφή JSON.")

    # Προσθήκη δομής καρτελών και για τα υπόλοιπα σούπερ μάρκετ
    for name, link in TARGET_SOURCES.items():
        if name == "e_katanalotis_api":
            continue
            
        # Ενδεικτική καρτέλα δομής για κάθε αλυσίδα
        all_offers.append({
            "supermarket": name.upper(),
            "image_url": "https://via.placeholder.com/150",
            "product_title": f"Προσφορά | Ενδεικτικό προϊόν από {name}",
            "offer_price": "0.00 €",
            "unit_or_original_price": "0.00 €",
            "source_link": link
        })

    # Αποθήκευση στο clean_offers.json με ακριβώς αυτή τη μορφή
    output_filename = "clean_offers.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_offers, f, ensure_ascii=False, indent=4)

    print(f"\nΗ διαδικασία ολοκληρώθηκε! Αποθηκεύτηκαν {len(all_offers)} καρτέλες προσφορών στο '{output_filename}'.")

if __name__ == "__main__":
    main()
