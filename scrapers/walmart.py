from playwright.sync_api import sync_playwright, TimeoutError


class WalmartScraper:

    BASE_URL = "https://www.walmart.com/search?q={}"

    def __init__(self, headless=False):

        self.current_query = None
        self.current_url = None

        self.playwright = sync_playwright().start()

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir="./walmart_profile",
            headless=headless,
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )

        self.page = self.context.new_page()


    def search(self, query: str) -> bool:

        self.current_query = query
        self.current_url = self.BASE_URL.format(
            query.replace(" ", "+")
        )

        return self._load_page(self.current_url)
    

    def refresh(self) -> bool:

        if self.current_url is None:
            raise RuntimeError("No search has been performed yet.")

        return self._load_page(self.current_url)

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

    def get_products(self):

        cards = self.page.locator("[data-item-id]")

        products = []

        for i in range(cards.count()):

            card = cards.nth(i)

            try:

                title = card.locator(
                    "[data-automation-id='product-title']"
                ).inner_text()

                price = card.locator(
                    "[data-automation-id='product-price']"
                ).inner_text()

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

    def close(self):

        self.context.close()
        self.playwright.stop()