from scrapers.walmart import WalmartScraper

scraper = WalmartScraper()

if scraper.search("pokemon cards"):

    products = scraper.get_products()

    print(f"Found {len(products)} products.\n")

    for product in products:

        print(product["title"])
        print(product["price"])
        print(product["url"])
        print()

scraper.close()