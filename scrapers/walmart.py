from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright, TimeoutError


class WalmartScraper:

    SEARCH_URL = "https://www.walmart.com/search/?query={query}&page={page}"

    def __init__(self, headless=False):

        self.current_query = None
        self.current_page = None
        self.max_pages = 1
        self.current_url = None

        self.playwright = sync_playwright().start()

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir="./walmart_profile",
            headless=headless,
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )

        self.page = self.context.new_page()


    def search(self, query: str, max_pages: int = 1) -> bool:

        self.current_query = query
        self.max_pages = max_pages if max_pages >= 1 else 1
        self.current_page = 1
        self.current_url = self._build_search_url(self.current_page)

        return self._load_page(self.current_url)
    

    def refresh(self) -> bool:

        if self.current_url is None:
            raise RuntimeError("No search has been performed yet.")

        return self._load_page(self.current_url)


    NEXT_PAGE_SELECTORS = [
        "button[aria-label='Next page']",
        "button[aria-label='Next']",
        "a[aria-label='Next']"
    ]

    def go_to_page(self, page: int) -> bool:

        if self.current_query is None:
            raise RuntimeError("No search has been performed yet.")

        if page < 1:
            raise ValueError("Page number must be 1 or greater.")

        if self.current_page is not None and page == self.current_page + 1:
            if self._click_next_page():
                self.current_page = page
                return True

        self.current_page = page
        self.current_url = self._build_search_url(page)

        return self._load_page(self.current_url)


    def _click_next_page(self) -> bool:

        for selector in self.NEXT_PAGE_SELECTORS:
            next_button = self.page.locator(selector).first
            if next_button.count() and next_button.is_enabled():
                try:
                    next_button.click()
                    self.page.wait_for_load_state("networkidle", timeout=15000)
                    self.page.wait_for_timeout(800)
                    return True
                except Exception:
                    continue

        return False


    def _build_search_url(self, page: int) -> str:

        return self.SEARCH_URL.format(
            query=quote_plus(self.current_query),
            page=page
        )


    def _load_page(self, url: str) -> bool:

        self.page.goto(
            url,
            wait_until="domcontentloaded"
        )

        try:

            self.page.wait_for_selector(
                "[data-item-id]",
                timeout=15000
            )

            return True

        except TimeoutError:

            print("Couldn't find product cards.")
            return False

    def get_products(self, max_pages: int | None = None):

        if self.current_query is None:
            raise RuntimeError("No search has been performed yet.")

        max_pages = max_pages or self.max_pages
        if max_pages < 1:
            max_pages = 1

        products = []
        seen_urls = set()

        for page in range(1, max_pages + 1):
            if page != self.current_page:
                if not self.go_to_page(page):
                    break

            page_products = self._extract_products_from_current_page()
            for product in page_products:
                if product["url"] not in seen_urls:
                    seen_urls.add(product["url"])
                    products.append(product)

        return products


    def _extract_products_from_current_page(self):

        cards = self.page.locator("[data-item-id]")

        products = []

        for i in range(cards.count()):

            card = cards.nth(i)

            try:

                title = card.locator(
                    "[data-automation-id='product-title']"
                ).inner_text().strip()

                price = card.locator(
                    "[data-automation-id='product-price']"
                ).inner_text().strip()

                image = card.locator(
                    "img"
                ).first.get_attribute("src")

                url = card.locator(
                    "a"
                ).first.get_attribute("href")

                if url and url.startswith("/"):
                    url = "https://www.walmart.com" + url

                products.append({
                    "title": title,
                    "price": price,
                    "image": image,
                    "url": url
                })

            except Exception:
                continue

        return products


    def save_products(self, products, filename):

        with open(filename, "w", encoding="utf-8") as file:
            file.write(f"Search results for '{self.current_query}'\n")
            file.write(f"Products saved: {len(products)}\n")
            file.write(f"Pages scraped: {max(1, self.max_pages)}\n\n")

            for product in products:
                file.write(f"Title: {product['title']}\n")
                file.write(f"Price: {product['price']}\n")
                file.write(f"URL: {product['url']}\n")
                file.write(f"Image: {product['image']}\n")
                file.write("-" * 80 + "\n")

        return filename


    def close(self):

        self.context.close()
        self.playwright.stop()