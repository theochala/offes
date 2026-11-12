#!/usr/bin/env python3
"""
Supermarket Offers Scraper (Greece)
===================================
Συλλέγει προσφορές από μεγάλα ελληνικά σούπερ μάρκετ (Σκλαβενίτης, ΑΒ Βασιλόπουλος,
My Market, Μασούτης, Κρητικός) και αποθηκεύει τα αποτελέσματα σε CSV και JSON.
"""

import csv
import json
import logging
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Ρύθμιση καταγραφής (logging)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class OfferItem:
    supermarket: str
    title: str
    original_price: Optional[float]
    offer_price: Optional[float]
    discount_label: str
    url: str
    scraped_at: str


def clean_price(price_str: str) -> Optional[float]:
    """Μετατρέπει κείμενο τιμής (π.χ. '3,45 €') σε float (3.45)."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^0-9,.]", "", price_str).replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


class SupermarketOffersScraper:
    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "el-GR,el;q=0.9,en;q=0.8",
            }
        )
        self.offers: List[OfferItem] = []

    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            logger.warning(f"Αποτυχία φόρτωσης {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # 1. ΣΚΛΑΒΕΝΙΤΗΣ (sklavenitis.gr)
    # ------------------------------------------------------------------
    def scrape_sklavenitis(self, max_pages: int = 3):
        logger.info("Ξεκινάει η συλλογή από Σκλαβενίτη...")
        base_url = "https://www.sklavenitis.gr"
        for page in range(1, max_pages + 1):
            url = f"{base_url}/sylloges/prosfores/?pg={page}"
            soup = self._get_soup(url)
            if not soup:
                break

            products = soup.select(".product")
            if not products:
                break

            for item in products:
                title_el = item.select_one(".product__title a, .product__title")
                price_el = item.select_one(".price, .product__price")
                old_price_el = item.select_one(".deleted-price, .product__old-price")
                badge_el = item.select_one(".product__discount, .discount-tag")

                title = title_el.get_text(strip=True) if title_el else "Άγνωστο προϊόν"
                href = title_el.get("href", "") if title_el and title_el.name == "a" else ""
                offer_price = clean_price(price_el.get_text()) if price_el else None
                orig_price = clean_price(old_price_el.get_text()) if old_price_el else None
                discount = badge_el.get_text(strip=True) if badge_el else "Προσφορά"

                self.offers.append(
                    OfferItem(
                        supermarket="Σκλαβενίτης",
                        title=title,
                        original_price=orig_price,
                        offer_price=offer_price,
                        discount_label=discount,
                        url=urljoin(base_url, href),
                        scraped_at=datetime.now().isoformat(timespec="seconds"),
                    )
                )
            time.sleep(self.delay)

    # ------------------------------------------------------------------
    # 2. ΑΒ ΒΑΣΙΛΟΠΟΥΛΟΣ (ab.gr)
    # ------------------------------------------------------------------
    def scrape_ab(self, max_pages: int = 3):
        logger.info("Ξεκινάει η συλλογή από ΑΒ Βασιλόπουλο...")
        base_url = "https://www.ab.gr"
        for page in range(max_pages):
            url = f"{base_url}/el/search/promotions?page={page}"
            soup = self._get_soup(url)
            if not soup:
                break

            cards = soup.select("[data-testid='product-block'], .product-item")
            if not cards:
                break

            for card in cards:
                title_el = card.select_one("[data-testid='product-block-name'], .product-title")
                price_el = card.select_one("[data-testid='product-block-price'], .current-price")
                old_price_el = card.select_one("[data-testid='product-block-old-price'], .old-price")
                badge_el = card.select_one("[data-testid='product-promo-badge'], .promo-badge")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else "Άγνωστο προϊόν"
                href = link_el.get("href", "") if link_el else ""
                offer_price = clean_price(price_el.get_text()) if price_el else None
                orig_price = clean_price(old_price_el.get_text()) if old_price_el else None
                discount = badge_el.get_text(strip=True) if badge_el else "Προσφορά ΑΒ"

                self.offers.append(
                    OfferItem(
                        supermarket="ΑΒ Βασιλόπουλος",
                        title=title,
                        original_price=orig_price,
                        offer_price=offer_price,
                        discount_label=discount,
                        url=urljoin(base_url, href),
                        scraped_at=datetime.now().isoformat(timespec="seconds"),
                    )
                )
            time.sleep(self.delay)

    # ------------------------------------------------------------------
    # 3. MY MARKET (mymarket.gr)
    # ------------------------------------------------------------------
    def scrape_mymarket(self, max_pages: int = 3):
        logger.info("Ξεκινάει η συλλογή από My Market...")
        base_url = "https://www.mymarket.gr"
        for page in range(1, max_pages + 1):
            url = f"{base_url}/offers?page={page}"
            soup = self._get_soup(url)
            if not soup:
                break

            cards = soup.select(".product-card, .product-teaser")
            if not cards:
                break

            for card in cards:
                title_el = card.select_one(".product-title, h3 a")
                price_el = card.select_one(".price-final, .product-price")
                old_price_el = card.select_one(".price-initial, .old-price")
                badge_el = card.select_one(".offer-label, .discount-badge")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else "Άγνωστο προϊόν"
                href = link_el.get("href", "") if link_el else ""
                offer_price = clean_price(price_el.get_text()) if price_el else None
                orig_price = clean_price(old_price_el.get_text()) if old_price_el else None
                discount = badge_el.get_text(strip=True) if badge_el else "Προσφορά"

                self.offers.append(
                    OfferItem(
                        supermarket="My Market",
                        title=title,
                        original_price=orig_price,
                        offer_price=offer_price,
                        discount_label=discount,
                        url=urljoin(base_url, href),
                        scraped_at=datetime.now().isoformat(timespec="seconds"),
                    )
                )
            time.sleep(self.delay)

    # ------------------------------------------------------------------
    # 4. ΜΑΣΟΥΤΗΣ (masoutis.gr)
    # ------------------------------------------------------------------
    def scrape_masoutis(self, max_pages: int = 3):
        logger.info("Ξεκινάει η συλλογή από Μασούτη...")
        base_url = "https://www.masoutis.gr"
        for page in range(1, max_pages + 1):
            url = f"{base_url}/offers?page={page}"
            soup = self._get_soup(url)
            if not soup:
                break

            cards = soup.select(".product-box, .item-product")
            if not cards:
                break

            for card in cards:
                title_el = card.select_one(".product-title, .item-title")
                price_el = card.select_one(".final-price, .item-price")
                old_price_el = card.select_one(".initial-price, .old-price")
                badge_el = card.select_one(".discount-percent, .offer-tag")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else "Άγνωστο προϊόν"
                href = link_el.get("href", "") if link_el else ""
                offer_price = clean_price(price_el.get_text()) if price_el else None
                orig_price = clean_price(old_price_el.get_text()) if old_price_el else None
                discount = badge_el.get_text(strip=True) if badge_el else "Προσφορά"

                self.offers.append(
                    OfferItem(
                        supermarket="Μασούτης",
                        title=title,
                        original_price=orig_price,
                        offer_price=offer_price,
                        discount_label=discount,
                        url=urljoin(base_url, href),
                        scraped_at=datetime.now().isoformat(timespec="seconds"),
                    )
                )
            time.sleep(self.delay)

    # ------------------------------------------------------------------
    # 5. ΚΡΗΤΙΚΟΣ (kritikos-sm.gr)
    # ------------------------------------------------------------------
    def scrape_kritikos(self, max_pages: int = 3):
        logger.info("Ξεκινάει η συλλογή από Κρητικό...")
        base_url = "https://kritikos-sm.gr"
        for page in range(1, max_pages + 1):
            url = f"{base_url}/offers/?page={page}"
            soup = self._get_soup(url)
            if not soup:
                break

            cards = soup.select(".product-card, .product-item")
            if not cards:
                break

            for card in cards:
                title_el = card.select_one(".product-title, h2, h3")
                price_el = card.select_one(".product-price, .price")
                old_price_el = card.select_one(".old-price, del")
                badge_el = card.select_one(".badge, .discount")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else "Άγνωστο προϊόν"
                href = link_el.get("href", "") if link_el else ""
                offer_price = clean_price(price_el.get_text()) if price_el else None
                orig_price = clean_price(old_price_el.get_text()) if old_price_el else None
                discount = badge_el.get_text(strip=True) if badge_el else "Προσφορά"

                self.offers.append(
                    OfferItem(
                        supermarket="Κρητικός",
                        title=title,
                        original_price=orig_price,
                        offer_price=offer_price,
                        discount_label=discount,
                        url=urljoin(base_url, href),
                        scraped_at=datetime.now().isoformat(timespec="seconds"),
                    )
                )
            time.sleep(self.delay)

    def run_all(self, max_pages_per_store: int = 3):
        self.scrape_sklavenitis(max_pages=max_pages_per_store)
        self.scrape_ab(max_pages=max_pages_per_store)
        self.scrape_mymarket(max_pages=max_pages_per_store)
        self.scrape_masoutis(max_pages=max_pages_per_store)
        self.scrape_kritikos(max_pages=max_pages_per_store)
        logger.info(f"Συνολικές προσφορές που συλλέχθηκαν: {len(self.offers)}")

    def export_csv(self, filename: str = "supermarket_offers.csv"):
        if not self.offers:
            logger.warning("Δεν βρέθηκαν προσφορές για εξαγωγή σε CSV.")
            return
        fieldnames = list(asdict(self.offers[0]).keys())
        with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for offer in self.offers:
                writer.writerow(asdict(offer))
        logger.info(f"Αποθηκεύτηκε το αρχείο CSV: {filename}")

    def export_json(self, filename: str = "supermarket_offers.json"):
        with open(filename, mode="w", encoding="utf-8") as f:
            json.dump([asdict(o) for o in self.offers], f, ensure_ascii=False, indent=2)
        logger.info(f"Αποθηκεύτηκε το αρχείο JSON: {filename}")


if __name__ == "__main__":
    scraper = SupermarketOffersScraper(delay=1.5)
    scraper.run_all(max_pages_per_store=2)
    scraper.export_csv("supermarket_offers.csv")
    scraper.export_json("supermarket_offers.json")
