from urllib.parse import quote_plus
from .base_scraper import BaseScraper


class WalmartScraper(BaseScraper):
    SEARCH_URL = "https://www.walmart.com/search/?query={query}&page={page}"
    PRODUCT_CARD_SELECTOR = "[data-item-id]"
    TITLE_SELECTOR = "[data-automation-id='product-title']"
    PRICE_SELECTOR = "[data-automation-id='product-price']"
    IMAGE_SELECTOR = "img"
    URL_SELECTOR = "a"
    BLOCKED_URL_PREFIX = "https://www.walmart.com/blocked"

    def _build_search_url(self, page: int) -> str:
        return self.SEARCH_URL.format(
            query=quote_plus(self.current_query),
            page=page,
        )

    def _load_page(self, url: str) -> bool:
        if not super()._load_page(url):
            return False

        if self.page.url.startswith(self.BLOCKED_URL_PREFIX):
            print("Walmart blocked the request. Please wait or try a different session.")
            return False

        return True

    def _normalize_url(self, url: str | None) -> str | None:
        if not url:
            return url
        if url.startswith("/"):
            return "https://www.walmart.com" + url
        return url
