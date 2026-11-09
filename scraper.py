import json
import time

# Σημείωση: Στην παραγωγή εδώ χρησιμοποιείς BeautifulSoup/Playwright για να κάνεις scrape τα eshop.
# Για το παράδειγμα, δομούμε τα δεδομένα ακριβώς όπως θα επιστρέφονταν από τα σούπερ μάρκετ.

products_data = [
    {
        "id": "1",
        "name": "Γάλα Φρέσκο Πλήρες 1L",
        "brand": "ΟΛΥΜΠΟΣ",
        "category": "Γαλακτοκομικά",
        "supermarket": "Σκλαβενίτης",
        "original_price": 1.75,
        "offer_price": 1.35,
        "image": "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=300"
    },
    {
        "id": "2",
        "name": "Γάλα Φρέσκο Πλήρες 1L",
        "brand": "ΟΛΥΜΠΟΣ",
        "category": "Γαλακτοκομικά",
        "supermarket": "ΑΒ Βασιλόπουλος",
        "original_price": 1.78,
        "offer_price": 1.42,
        "image": "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=300"
    },
    {
        "id": "3",
        "name": "Ελαιόλαδο Έξτρα Παρθένο 1L",
        "brand": "ΧΩΡΙΟ",
        "category": "Τρόφιμα",
        "supermarket": "Μασούτης",
        "original_price": 12.50,
        "offer_price": 9.90,
        "image": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=300"
    },
    {
        "id": "4",
        "name": "Ελαιόλαδο Έξτρα Παρθένο 1L",
        "brand": "ΧΩΡΙΟ",
        "category": "Τρόφιμα",
        "supermarket": "Σκλαβενίτης",
        "original_price": 12.20,
        "offer_price": 10.50,
        "image": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=300"
    },
    {
        "id": "5",
        "name": "Κάψουλες Καφέ Espresso 10τμχ",
        "brand": "NESPRESSO",
        "category": "Ποτά & Καφέδες",
        "supermarket": "MyMarket",
        "original_price": 4.80,
        "offer_price": 3.60,
        "image": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=300"
    },
    {
        "id": "6",
        "name": "Υγρό Πιάτων 500ml",
        "brand": "FAIRY",
        "category": "Καθαριστικά",
        "supermarket": "ΑΒ Βασιλόπουλος",
        "original_price": 2.90,
        "offer_price": 1.95,
        "image": "https://images.unsplash.com/photo-1585832770485-e68a5fcfad52?w=300"
    }
]

def save_products():
    print("Συλλογή προσφορών...")
    time.sleep(1)
    
    # Υπολογισμός ποσοστού έκπτωσης
    for item in products_data:
        discount = round(((item["original_price"] - item["offer_price"]) / item["original_price"]) * 100)
        item["discount_percent"] = discount

    with open("offers.json", "w", encoding="utf-8") as f:
        json.dump(products_data, f, ensure_ascii=False, indent=4)
        
    print("✅ Αποθηκεύτηκαν 6 προσφορές στο offers.json!")

if __name__ == "__main__":
    save_products()
