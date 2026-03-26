"""
YouTube qidiruv — Playwright async
"""

import asyncio
import logging
import random
from typing import List
from urllib.parse import quote_plus

from playwright.async_api import Page

from config import Config

logger = logging.getLogger(__name__)


class YouTubeSearch:
    """
    YouTube da qidirish va birinchi N ta video URL ni olish.
    """

    def __init__(self, page: Page):
        self.page = page

    async def search_and_get_urls(
            self, query: str, max_results: int = 10
    ) -> List[str]:
        """
        Qidirish va video URL larni qaytarish.

        Args:
            query: Qidiruv so'zi
            max_results: Nechta URL kerak

        Returns:
            Video URL lari ro'yxati
        """
        logger.info(f"Qidirish: '{query}'")

        try:
            await self._goto_youtube()
            await self._handle_consent()
            await self._do_search(query)
            return await self._collect_urls(max_results)
        except Exception as e:
            logger.error(f"Qidirishda xato: {e}", exc_info=True)
            # Fallback — to'g'ridan URL orqali
            try:
                url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                await self.page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                return await self._collect_urls(max_results)
            except Exception as e2:
                logger.error(f"Fallback ham ishlamadi: {e2}")
                return []

    async def _goto_youtube(self):
        await self.page.goto(
            "https://www.youtube.com",
            wait_until="domcontentloaded",
            timeout=Config.BROWSER_TIMEOUT * 1000,
        )
        await asyncio.sleep(random.uniform(2, 5))

    async def _handle_consent(self):
        """Cookie consent popup ni qabul qilish"""
        selectors = [
            'button:has-text("Accept all")',
            'button:has-text("Agree")',
            'tp-yt-paper-button#agree-button',
        ]
        for sel in selectors:
            try:
                btn = self.page.locator(sel).first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    await asyncio.sleep(1)
                    logger.debug("Consent qabul qilindi")
                    break
            except Exception:
                continue

    async def _do_search(self, query: str):
        """Qidiruv maydoniga yozish"""
        search_box = self.page.locator('input#search')
        await search_box.wait_for(state="visible", timeout=10000)
        await search_box.click()
        await asyncio.sleep(0.3)

        # Har bir harfni alohida yozish (inson kabi)
        for char in query:
            await search_box.type(char, delay=random.randint(50, 150))

        await asyncio.sleep(0.5)
        await self.page.keyboard.press("Enter")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)
        logger.info(f"Qidiruv natijasi yuklandi: '{query}'")

    async def _collect_urls(self, max_results: int) -> List[str]:
        """Natijalardan video URL larini olish"""
        # Bir oz scroll qilib lazy load ni ishga tushirish
        await self.page.evaluate("window.scrollBy(0, 400)")
        await asyncio.sleep(1)

        urls = []
        seen = set()

        # Barcha video renderer elementlarini topish
        renderers = await self.page.locator("ytd-video-renderer").all()
        logger.info(f"{len(renderers)} ta video renderer topildi")

        for renderer in renderers:
            if len(urls) >= max_results:
                break
            try:
                link = renderer.locator("a#video-title").first
                href = await link.get_attribute("href", timeout=3000)

                if not href:
                    continue
                if "watch?v=" not in href and "/shorts/" not in href:
                    continue

                full_url = f"https://www.youtube.com{href}" if href.startswith("/") else href
                if full_url in seen:
                    continue
                seen.add(full_url)
                title = await link.get_attribute("title") or ""
                urls.append(full_url)
                logger.info(f"  [{len(urls)}] {title[:60]}")
            except Exception as e:
                logger.debug(f"URL olishda xato: {e}")
                continue

        logger.info(f"Jami {len(urls)} ta URL topildi")
        return urls
