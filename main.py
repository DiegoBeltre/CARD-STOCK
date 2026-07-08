import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from scrapers.Pokemoncenter import PokemonCenterScraper
from scrapers.walmart import WalmartScraper

BASE_DIR = Path(__file__).resolve().parent
search_query = "pokemon cards"
refresh_interval = 10

SCRAPERS = {
    "walmart": WalmartScraper,
    "pokemoncenter": PokemonCenterScraper,
}

proxy_server = None
proxy_username = None
proxy_password = None


def load_previous_cache(cache_file: Path):
    if not cache_file.exists():
        return {}

    try:
        with cache_file.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_cache(products, cache_file: Path):
    cache = {}
    for product in products:
        key = product["url"] or product["title"]
        cache[key] = {
            "title": product["title"],
            "price": product["price"],
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


def write_results(products, prev_cache, output_file: Path, json_output_file: Path):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{time.strftime('%H:%M:%S')}] Found {len(products)} products.\n")

    structured_results = []
    with output_file.open("w", encoding="utf-8") as file:
        file.write(f"[{current_time}] {len(products)} products\n\n")

        for product in products:
            key = product["url"] or product["title"]
            previous_price = prev_cache.get(key, {}).get("price")
            change = format_change(product["price"], previous_price)

            entry = {
                "title": product["title"],
                "price": product["price"],
                "previous_price": previous_price or None,
                "change": change,
                "url": product["url"],
                "timestamp": current_time,
            }
            structured_results.append(entry)

            lines = [
                f"Title: {product['title']}",
                f"Price: {product['price']}",
                f"Previous price: {previous_price or 'N/A'}",
                f"Change: {change}",
                f"URL: {product['url']}",
                "",
            ]

            print("\n".join(lines))
            file.write("\n".join(lines) + "\n")

    with json_output_file.open("w", encoding="utf-8") as file:
        json.dump(structured_results, file, indent=2, ensure_ascii=False)

    print(f"Saved text results to {output_file}")
    print(f"Saved JSON results to {json_output_file}")


def make_scraper(target_site: str):
    scraper_cls = SCRAPERS.get(target_site)
    if not scraper_cls:
        raise ValueError(f"Unsupported target site: {target_site}")

    return scraper_cls(
        proxy_server=proxy_server,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
    )


def run_single_site(target_site: str):
    output_file = BASE_DIR / f"{target_site}_products.txt"
    json_output_file = BASE_DIR / f"{target_site}_products.json"
    cache_file = BASE_DIR / f"{target_site}_products_prev.json"

    prev_cache = load_previous_cache(cache_file)
    scraper = make_scraper(target_site)
    max_pages = 3

    try:
        if not scraper.search(search_query, max_pages=max_pages):
            print("Initial search failed. Waiting 30 seconds and retrying refresh...")
            time.sleep(30)
            if not scraper.refresh():
                raise RuntimeError("Unable to load the target page after retry.")

        print(f"Searching Pages for {target_site}\n")

        while True:
            products = scraper.get_products(max_pages=max_pages)
            write_results(products, prev_cache, output_file, json_output_file)
            prev_cache = save_cache(products, cache_file)

            print(f"Waiting {refresh_interval} seconds before reloading...\n")
            time.sleep(refresh_interval)

            if not scraper.refresh():
                print("Page refresh failed. Waiting 30 seconds before retrying...")
                time.sleep(30)
                if not scraper.refresh():
                    raise RuntimeError("Unable to refresh the target page.")

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        scraper.close()


def run_both_sites():
    sites = ["walmart", "pokemoncenter"]
    processes = []

    for site in sites:
        process = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "main.py"), site],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append((site, process))
        print(f"Started {site} with PID {process.pid}")

    try:
        while True:
            for site, process in processes:
                if process.poll() is not None:
                    print(f"{site} exited with code {process.returncode}; restarting...")
                    new_process = subprocess.Popen(
                        [sys.executable, str(BASE_DIR / "main.py"), site],
                        cwd=str(BASE_DIR),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                    processes[processes.index((site, process))] = (site, new_process)
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping all scraper processes...")
        for _, process in processes:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        print("All scraper processes stopped.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default=None)
    parser.add_argument("--both", action="store_true", help="Run both Walmart and Pokémon Center scrapers")
    args = parser.parse_args()

    if args.both or args.site is None:
        run_both_sites()
        return

    run_single_site(args.site.lower())


if __name__ == "__main__":
    main()