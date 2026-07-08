from urllib.parse import quote_plus
from .base_scraper import BaseScraper


class PokemonCenterScraper(BaseScraper):
    SEARCH_URL = "https://www.pokemoncenter.com/search?q={query}&page={page}"
    PRODUCT_CARD_SELECTOR = "article"
    TITLE_SELECTOR = "img"
    PRICE_SELECTOR = ".price"
    IMAGE_SELECTOR = "img"
    URL_SELECTOR = "a"

    def _load_page(self, url: str) -> bool:
        if not super()._load_page(url):
            return False

        page_text = self.page.content().lower()
        if "incapsula" in page_text or "/_incapsula_resource" in self.page.url.lower():
            print("Pokémon Center is blocking this session with Incapsula, so no product cards can be scraped from this IP/session.")
            return False

        if self.page.locator(self.PRODUCT_CARD_SELECTOR).count() == 0:
            print("Pokémon Center did not return any product cards for this search.")
            return False

        return True

    def _build_search_url(self, page: int) -> str:
        return self.SEARCH_URL.format(
            query=quote_plus(self.current_query),
            page=page,
        )

    def _normalize_url(self, url: str | None) -> str | None:
        if not url:
            return None

        if url.startswith("/"):
            return "https://www.pokemoncenter.com" + url

        return url

    def get_products(self, max_pages: int | None = None):
        max_pages = max_pages or self.max_pages or 1
        if max_pages < 1:
            max_pages = 1

        products = []
        seen_urls = set()

        for page_number in range(1, max_pages + 1):
            self.current_url = self._build_search_url(page_number)
            self.current_page = page_number

            if not self._load_page(self.current_url):
                print(f"Failed to load page {page_number}. Stopping pagination.")
                break

            page_products = self._extract_products_from_current_page()
            for product in page_products:
                url = product["url"]
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    products.append(product)

            if page_number < max_pages:
                self.page.wait_for_timeout(10000)

        return products

    def _extract_products_from_current_page(self):
        cards = self.page.locator(self.PRODUCT_CARD_SELECTOR)
        products = []

        for index in range(cards.count()):
            card = cards.nth(index)
            try:
                image = card.locator(self.IMAGE_SELECTOR).first
                title = (image.get_attribute("alt") or "").strip()
                image_url = image.get_attribute("src")

                price_locator = card.locator(self.PRICE_SELECTOR)
                price = price_locator.first.inner_text().strip() if price_locator.count() else ""

                url = self._normalize_url(card.locator(self.URL_SELECTOR).first.get_attribute("href"))

                sold_out = card.locator(
                    ".product-image-oos--Lae0t, .out-of-stock, .product-card__badge--out-of-stock"
                ).count() > 0

                if not title and not price and not url:
                    continue

                products.append(
                    {
                        "title": title,
                        "price": price,
                        "image": image_url,
                        "url": url,
                        "in_stock": not sold_out,
                    }
                )
            except Exception as exc:
                print(f"Skipping card: {exc}")

        return products