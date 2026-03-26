"""
Playwright brauzer boshqaruvi — async
"""

import logging
import random
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from config import Config

logger = logging.getLogger(__name__)

# Real brauzer User-Agent lari
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class BrowserManager:
    """
    Playwright async brauzer manager.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self) -> "BrowserManager":
        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-notifications",
                "--mute-audio",
            ],
        )

        self._context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            # Bot aniqlanishini qiyinlashtirish
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        # navigator.webdriver = false qilish
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)

        logger.info(f"Playwright brauzer ochildi (headless={self.headless})")
        return self

    async def new_page(self) -> Page:
        """Yangi sahifa yaratish"""
        if not self._context:
            raise RuntimeError("Browser context is not initialized")

        page = await self._context.new_page()
        page.set_default_timeout(Config.BROWSER_TIMEOUT * 1000)
        return page

    async def close(self):
        """Brauzer va barcha resurslarni yopish"""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("Playwright brauzer yopildi")
        except Exception as e:
            logger.warning(f"Brauzer yopishda xato: {e}")

    # Context manager
    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, *_):
        await self.close()
