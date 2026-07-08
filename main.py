import json
import time
from pathlib import Path
from scrapers.walmart import WalmartScraper

BASE_DIR = Path(__file__).resolve().parent
search_query = "pokemon cards"
refresh_interval = 10  # seconds between reloads
output_file = BASE_DIR / "walmart_products.txt"
cache_file = BASE_DIR / "walmart_products_prev.json"

# Add more site scrapers here.
SCRAPERS = {
    "walmart": WalmartScraper,
}

target_site = "walmart"

# Change this to a different site when you add another scraper.
target_site = "walmart"

proxy_server = None
proxy_username = None
proxy_password = None


def load_previous_cache():
    if not cache_file.exists():
        return {}

    try:
        with cache_file.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_cache(products):
    cache = {}
    for product in products:
        key = product["url"] or product["title"]
        cache[key] = {
            "title": product["title"],
            "price": product["price"]
        }

    with cache_file.open("w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2, ensure_ascii=False)

    return cache


def format_change(current_price, previous_price):
    if previous_price is None:
        return "NEW"
    if previous_price == current_price:
        return "same"
    return f"changed from {previous_price}"


def write_results(products, prev_cache):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{time.strftime('%H:%M:%S')}] Found {len(products)} products.\n")

    with output_file.open("w", encoding="utf-8") as file:
        file.write(f"[{current_time}] {len(products)} products\n\n")

        for product in products:
            key = product["url"] or product["title"]
            previous_price = prev_cache.get(key, {}).get("price")
            change = format_change(product["price"], previous_price)

            lines = [
                f"Title: {product['title']}",
                f"Price: {product['price']}",
                f"Previous price: {previous_price or 'N/A'}",
                f"Change: {change}",
                f"URL: {product['url']}",
                ""
            ]

            entry = "\n".join(lines)
            print(entry)
            file.write(entry + "\n")

    print(f"Saved results to {output_file}")


def make_scraper():
    scraper_cls = SCRAPERS.get(target_site)
    if not scraper_cls:
        raise ValueError(f"Unsupported target site: {target_site}")

    return scraper_cls(
        proxy_server=proxy_server,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
    )


def main():
    prev_cache = load_previous_cache()
    scraper = make_scraper()
    max_pages = 3

    try:
        if not scraper.search(search_query, max_pages=max_pages):
            print("Initial search failed. Waiting 30 seconds and retrying refresh...")
            time.sleep(30)
            if not scraper.refresh():
                raise RuntimeError("Unable to load Walmart page after retry.")

        print(f"Searching Pages\n")

        while True:
            products = scraper.get_products(max_pages=max_pages)
            write_results(products, prev_cache)
            prev_cache = save_cache(products)

            print(f"Waiting {refresh_interval} seconds before reloading...\n")
            time.sleep(refresh_interval)

            if not scraper.refresh():
                print("Page refresh failed. Waiting 30 seconds before retrying...")
                time.sleep(30)
                if not scraper.refresh():
                    raise RuntimeError("Unable to refresh Walmart page.")

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()