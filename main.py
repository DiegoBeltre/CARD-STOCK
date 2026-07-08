from scrapers.walmart import WalmartScraper

scraper = WalmartScraper()
search_query = "pokemon cards"
max_pages = 3

if scraper.search(search_query, max_pages=max_pages):

    print(f"Searching '{search_query}' across {max_pages} pages...\n")

    products = []
    seen_urls = set()

    for page in range(1, max_pages + 1):
        if page != 1:
            print(f"Loading page {page}/{max_pages}...")
            if not scraper.go_to_page(page):
                print(f"Stopped after page {page - 1}: next page failed to load.")
                break

        page_products = scraper._extract_products_from_current_page()
        print(f"Page {page}: found {len(page_products)} products")

        for product in page_products:
            if product["url"] not in seen_urls:
                seen_urls.add(product["url"])
                products.append(product)

    output_file = "walmart_products.txt"
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(f"Found {len(products)} products.\n\n")

        for product in products:
            line = f"{product['title']}\n{product['price']}\n{product['url']}\n\n"
            print(line, end="")
            file.write(line)

    print(f"Saved results to {output_file}")

scraper.close()