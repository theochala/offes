      const seen = new Set();
      const priceRx = /\\\\d{1,4}[.,]\\\\d{2}\\\\s*€/;
      const nodes = document.querySelectorAll(
        '[data-product], [class*=product], [class*=Product], article, li'
      );
      for (const el of nodes) {
        const text = (el.innerText || '').replace(/\\\\s+/g, ' ').trim();
        if (!text || text.length < 8 || text.length > 700 || !priceRx.test(text)) continue;
        const img = el.querySelector('img');
        const image = img ? (img.currentSrc || img.src || img.dataset.src ||
          img.getAttribute('data-lazy-src') || '') : '';
        const link = el.querySelector('a[href]');
        const href = link ? link.href : '';
        const key = text + '|' + image;
        if (!seen.has(key)) {
          seen.add(key);
          out.push({text, image, href});
        }
      }
      return out;
    }""")

def scrape_store(browser, name, url):
    print(f"Συλλογή: {name} — {url}")
    context = browser.new_context(
        locale="el-GR",
        viewport={"width": 1440, "height": 1000},
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    page = context.new_page()
    offers = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        # Try common consent controls without failing the scrape.
        for selector in [
            "button:has-text('Αποδοχή')", "button:has-text('Accept')",
            "button:has-text('Συμφωνώ')", "#onetrust-accept-btn-handler"
        ]:
            try:
                page.locator(selector).first.click(timeout=1200)
                break
            except Exception:
                pass

        # Scroll progressively to trigger lazy loading.
        previous_height = 0
        for _ in range(18):
            height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(900)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == previous_height and new_height == height:
                break
            previous_height = new_height
        page.evaluate("window.scrollTo(0, 0)")
        raw = extract_cards(page)

        for item in raw:
            text = item.get("text", "")
            if any(word in text.lower() for word in INVALID_TEXT):
                continue
            prices = PRICE_RE.findall(text)
            if not prices:
                continue
            title = clean_title(text)
            image = item.get("image") or ""
            if image.startswith("//"):
                image = "https:" + image
            elif image.startswith("/"):
                image = urljoin(url, image)
            if not title or len(title) < 4:
                continue
            offers.append({
                "title": title,
                "price": normalize_price(prices[-1]) + " €",
                "all_prices": [normalize_price(p) + " €" for p in prices],
                "image": image if image.startswith("http") else "",
                "supermarket": name,
                "product_url": item.get("href", ""),
                "source_url": url
            })
    except PlaywrightTimeoutError:
        print(f"  Timeout κατά τη φόρτωση: {name}")
    except Exception as exc:
        print(f"  Σφάλμα {name}: {exc}")
    finally:
        context.close()

    # Dedupe within store
    unique, seen = [], set()
    for offer in offers:
        key = (offer["supermarket"], offer["title"], offer["price"])
        if key not in seen:
            seen.add(key)
            unique.append(offer)
    print(f"  -> {len(unique)} πιθανές προσφορές")
    return unique

def main():
    all_offers = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for name, url in STORES:
                all_offers.extend(scrape_store(browser, name, url))
        finally:
            browser.close()

    # Final dedupe
    final, seen = [], set()
    for offer in all_offers:
        key = (offer["supermarket"], offer["title"], offer["price"])
        if key not in seen:
            seen.add(key)
            final.append(offer)

    output = Path("clean_offers.json")
    output.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\\nΑποθηκεύτηκαν {len(final)} εγγραφές στο {output.resolve()}")

if __name__ == "__main__":
    main()
