        const seen = new Set();
        const nodes = document.querySelectorAll('[class*=product], [class*=Product], article, li');
        for (const el of nodes) {
            const text = (el.innerText || '').replace(/\\\\s+/g, ' ').trim();
            if (!text || text.length > 700 || !/\\\\d{1,4}[.,]\\\\d{2}\\\\s*€/.test(text)) continue;
            const img = el.querySelector('img');
            const image = img ? (img.currentSrc || img.src || img.dataset.src || '') : '';
            const a = el.querySelector('a[href]');
            const href = a ? a.href : '';
            const key = text + '|' + image;
            if (!seen.has(key)) {
                seen.add(key);
                results.push({text, image, href});
            }
        }
        return results;
    }""")

def scrape_store(browser, name, url):
    print(f"Scraping {name}...")
    offers = []
    context = browser.new_context(locale="el-GR", viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        for selector in ["button:has-text('Αποδοχή')", "button:has-text('Accept')",
                         "button:has-text('Συμφωνώ')", "#onetrust-accept-btn-handler"]:
            try:
                page.locator(selector).first.click(timeout=1000)
                break
            except Exception:
                pass
        old_height = 0
        for _ in range(12):
            height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(700)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == old_height == height:
                break
            old_height = new_height

        for item in extract_cards(page):
            text = item["text"]
            if any(word in text.lower() for word in INVALID):
                continue
            prices = PRICE_RE.findall(text)
            if not prices:
                continue
            title = clean_title(text)
            if len(title) < 4:
                continue
            image = item.get("image", "")
            if image.startswith("//"):
                image = "https:" + image
            elif image.startswith("/"):
                image = urljoin(url, image)
            offers.append({
                "title": title,
                "price": prices[-1].replace(".", ",") + " €",
                "all_prices": [p.replace(".", ",") + " €" for p in prices],
                "image": image if image.startswith("http") else "",
                "supermarket": name,
                "product_url": item.get("href", ""),
                "source_url": url
            })
    except PlaywrightTimeoutError:
        print(f"Timeout: {name}")
    except Exception as e:
        print(f"Error {name}: {e}")
    finally:
        context.close()

    unique, seen = [], set()
    for offer in offers:
        key = (offer["supermarket"], offer["title"], offer["price"])
        if key not in seen:
            seen.add(key)
            unique.append(offer)
    print(f" -> {len(unique)} products")
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

    final, seen = [], set()
    for offer in all_offers:
        key = (offer["supermarket"], offer["title"], offer["price"])
        if key not in seen:
            seen.add(key)
            final.append(offer)

    Path("clean_offers.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved {len(final)} offers to clean_offers.json")

if __name__ == "__main__":
    main()
