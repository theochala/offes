import json

offers_data = [
    {
        "supermarket": "KRITIKOS",
        "image_url": "https://via.placeholder.com/150",
        "product_title": "Διαθέσιμες προσφορές (kritikos)",
        "offer_price": "0.00 €",
        "unit_or_original_price": "—",
        "source_link": "https://kritikos-sm.gr/prosfores/"
    },
    {
        "supermarket": "SKLEVENITIS",
        "image_url": "https://via.placeholder.com/150",
        "product_title": "Διαθέσιμες προσφορές (sklevenitis)",
        "offer_price": "0.00 €",
        "unit_or_original_price": "—",
        "source_link": "https://www.sklavenitis.gr/prosfores/"
    },
    {
        "supermarket": "AB_VASSILOPOULOS",
        "image_url": "https://via.placeholder.com/150",
        "product_title": "Διαθέσιμες προσφορές (ab_vassilopoulos)",
        "offer_price": "0.00 €",
        "unit_or_original_price": "—",
        "source_link": "https://www.ab.gr/promotions"
    },
    {
        "supermarket": "MASOUTIS",
        "image_url": "https://via.placeholder.com/150",
        "product_title": "Διαθέσιμες προσφορές (masoutis)",
        "offer_price": "0.00 €",
        "unit_or_original_price": "—",
        "source_link": "https://www.masoutis.gr/offers"
    },
    {
        "supermarket": "LIDL",
        "image_url": "https://via.placeholder.com/150",
        "product_title": "Διαθέσιμες προσφορές (lidl)",
        "offer_price": "0.00 €",
        "unit_or_original_price": "—",
        "source_link": "https://www.lidl-hellas.gr/c/prosfores/a100000"
    }
]

file_name = "clean_offers.json"
with open(file_name, "w", encoding="utf-8") as f:
    json.dump(offers_data, f, ensure_ascii=False, indent=4)

print(f"{file_name} generated successfully.")
