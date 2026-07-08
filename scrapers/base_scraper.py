from abc import ABC, abstractmethod
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError


class BaseScraper(ABC):
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    BROWSER_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--start-maximized",
        "--disable-dev-shm-usage",
        "--disable-web-security"
    ]

    SEARCH_URL = None
    PRODUCT_CARD_SELECTOR = None
    TITLE_SELECTOR = None
    PRICE_SELECTOR = None
    IMAGE_SELECTOR = None
    URL_SELECTOR = None

    def __init__(
        self,
        headless=False,
        proxy_server: str | None = None,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
    ):
        self.current_query = None
        self.current_url = None
        self.current_page = 1
        self.max_pages = 1

        self.playwright = sync_playwright().start()

        proxy = None
        if proxy_server:
            proxy = {"server": proxy_server}
            if proxy_username and proxy_password:
                proxy["username"] = proxy_username
                proxy["password"] = proxy_password

        profile_dir = (
            Path(__file__).resolve().parent.parent
            / f"profile_{self.__class__.__name__.lower()}"
        )
        profile_dir.mkdir(parents=True, exist_ok=True)

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            user_agent=self.USER_AGENT,
            args=self.BROWSER_ARGS,
            ignore_https_errors=True,
            proxy=proxy,
        )

        self._apply_stealth()
        self.page = self.context.new_page()
        self.page.set_extra_http_headers(
            {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
                "DNT": "1",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )

    def _apply_stealth(self):
        self.context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters);
            """
        )

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

    @abstractmethod
    def _build_search_url(self, page: int) -> str:
        raise NotImplementedError

    def _load_page(self, url: str) -> bool:
        self.page.goto(url, wait_until="domcontentloaded")

        try:
            self.page.wait_for_selector(self.PRODUCT_CARD_SELECTOR, timeout=15000)
            self._human_scroll()
            self.page.wait_for_timeout(random.randint(900, 1500))
            return True
        except TimeoutError:
            print("Couldn't find product cards.")
            return False

    def get_products(self, max_pages: int | None = None):
        if self.current_query is None:
            raise RuntimeError("No search has been performed yet.")

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
                if product["url"] not in seen_urls:
                    seen_urls.add(product["url"])
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
                title = card.locator(self.TITLE_SELECTOR).inner_text().strip()
                price = card.locator(self.PRICE_SELECTOR).inner_text().strip()
                image = card.locator(self.IMAGE_SELECTOR).first.get_attribute("src")
                url = self._normalize_url(card.locator(self.URL_SELECTOR).first.get_attribute("href"))

                products.append(
                    {
                        "title": title,
                        "price": price,
                        "image": image,
                        "url": url,
                    }
                )
            except Exception:
                continue

        return products

    def _normalize_url(self, url: str | None) -> str | None:
        return url

    def _human_scroll(self):
        steps = random.randint(2, 4)
        for _ in range(steps):
            self.page.mouse.wheel(0, random.randint(200, 400))
            self.page.wait_for_timeout(random.randint(400, 900))

    def close(self):
        self.context.close()
        self.playwright.stop()
