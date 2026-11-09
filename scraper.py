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
    """Βοηθητική συνάρτηση για ασφαλή ανάκτηση σελίδας μέσω urllib"""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        print(f"   [HTTP Error] Σφάλμα {e.code} για το URL: {url}")
    except urllib.error.URLError as e:
        print(f"   [URL Error] Αποτυχία σύνδεσης ({e.reason}) για το URL: {url}")
    except Exception as e:
        print(f"   [Error] Απρόσμενο σφάλμα: {e}")
    return None

def main():
    all_offers = []

    print("1. Συλλογή προσφορών από e-Καταναλωτή...")
    api_url = TARGET_SOURCES["e_katanalotis_api"]
    api_data = fetch_url_safely(api_url)
    
    if api_data:
        try:
            data = json.loads(api_data)
            items = data.get("products", data if isinstance(data, list) else [])
            for item in items[:20]:
                all_offers.append({
                    "supermarket": item.get("supermarket", "e-Katanalotis"),
                    "product": item.get("name") or item.get("title", "Άγνωστο Προϊόν"),
                    "original_price": item.get("price"),
                    "offer_price": item.get("offer_price"),
                    "discount": item.get("discount"),
                    "source_link": api_url
                })
        except json.JSONDecodeError:
            print("   [Σφάλμα] Τα δεδομένα του API δεν είχαν μορφή JSON.")

    print("2. Σάρωση ιστοσελίδων σούπερ μάρκετ...")
    for name, link in TARGET_SOURCES.items():
        if name == "e_katanalotis_api":
            continue
            
        print(f"   - Άντληση από {name} ({link})...")
        html_content = fetch_url_safely(link)
        
        if html_content:
            # Καταχώρηση επιτυχούς ανάκτησης της σελίδας (χωρίς BeautifulSoup)
            all_offers.append({
                "supermarket": name,
                "product": "Σελίδα προσφορών προσπελάσιμη",
                "original_price": None,
                "offer_price": None,
                "discount": None,
                "source_link": link
            })
        else:
            all_offers.append({
                "supermarket": name,
                "product": "Αποτυχία πρόσβασης (Πιθανός αποκλεισμός βοτ/Cloudflare)",
                "original_price": None,
                "offer_price": None,
                "discount": None,
                "source_link": link
            })

    # Αποθήκευση στο clean_offers.json
    output_filename = "clean_offers.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_offers, f, ensure_ascii=False, indent=4)

    print(f"\nΗ διαδικασία ολοκληρώθηκε! Αποθηκεύτηκαν {len(all_offers)} εγγραφές στο '{output_filename}'.")

if __name__ == "__main__":
    main()
