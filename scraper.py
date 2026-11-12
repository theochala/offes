#!/usr/bin/env python3
"""
Supermarket Offers Scraper με Playwright (Greece)
==================================================
Χρησιμοποιεί Headless Browser για να παρακάμπτει περιορισμούς JavaScript και anti-bot.
"""

import csv
import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

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


class PlaywrightOffersScraper:
    def __init__(self):
        self.offers: List[OfferItem] = []

    def scrape_all(self):
        with sync_playwright() as p:
            # Εκκίνηση του browser σε headless mode
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                locale="el-GR"
            )
            page = context.new_page()

            # ------------------------------------------------------------------
            # 1. MY MARKET (mymarket.gr)
            # ------------------------------------------------------------------
            try:
                logger.info("Συλλογή από My Market...")
                page.goto("https://www.mymarket.gr/offers", timeout=45000)
                page.wait_for_timeout(4000)  # Αναμονή φόρτωσης JavaScript
                
                cards = page.locator(".product-card, .product-teaser, article").all()
                for card in cards[:30]:
                    try:
                        title = card.locator(".product-title, h3").inner_text(timeout=1000)
                        price = card.locator(".price-final, .product-price").inner_text(timeout=1000)
                        link = card.locator("a").get_attribute("href")
                        
                        self.offers.append(
                            OfferItem(
                                supermarket="My Market",
                                title=title.strip(),
                                original_price=None,
                                offer_price=clean_price(price),
                                discount_label="Προσφορά",
                                url=urljoin("https://www.mymarket.gr", link) if link else "",
                                scraped_at=datetime.now().isoformat(timespec="seconds"),
                            )
                        )
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Σφάλμα στο My Market: {e}")

            # ------------------------------------------------------------------
            # 2. ΜΑΣΟΥΤΗΣ (masoutis.gr)
            # ------------------------------------------------------------------
            try:
                logger.info("Συλλογή από Μασούτη...")
                page.goto("https://www.masoutis.gr/offers", timeout=45000)
                page.wait_for_timeout(4000)
                
                cards = page.locator(".product-box, .item-product, article").all()
                for card in cards[:30]:
                    try:
                        title = card.locator(".product-title, h3").inner_text(timeout=1000)
                        price = card.locator(".final-price, .price").inner_text(timeout=1000)
                        link = card.locator("a").get_attribute("href")
                        
                        self.offers.append(
                            OfferItem(
                                supermarket="Μασούτης",
                                title=title.strip(),
                                original_price=None,
                                offer_price=clean_price(price),
                                discount_label="Προσφορά",
                                url=urljoin("https://www.masoutis.gr", link) if link else "",
                                scraped_at=datetime.now().isoformat(timespec="seconds"),
                            )
                        )
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Σφάλμα στον Μασούτη: {e}")

            browser.close()
        
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
    scraper = PlaywrightOffersScraper()
    scraper.scrape_all()
    scraper.export_csv("supermarket_offers.csv")
    scraper.export_json("supermarket_offers.json")
