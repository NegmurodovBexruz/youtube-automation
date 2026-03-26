"""
Parallel scraping — Playwright async, bir vaqtda N ta sahifa
"""

import asyncio
import logging
from typing import List, Optional

from config import Config
from models.video import Video
from scraper.browser import BrowserManager
from scraper.video_parser import VideoParser
from scraper.comment_parser import CommentParser

logger = logging.getLogger(__name__)


async def _scrape_one(url: str, index: int, headless: bool) -> Optional[Video]:
    """
    Bitta video uchun alohida brauzer context ochib ma'lumot yig'ish.
    """
    async with BrowserManager(headless=headless) as bm:
        page = await bm.new_page()
        try:
            video = await VideoParser(page).parse_video(url)
            if video:
                comments = await CommentParser(page).get_top_comments(
                    max_comments=Config.MAX_COMMENTS
                )
                video.top_comments = comments
                logger.info(f"[{index}] ✓ {video.video_title[:50]}")
            return video
        except Exception as e:
            logger.error(f"[{index}] Xato ({url[:50]}): {e}")
            return None


class ParallelScraper:
    """
    Native async parallel scraping.
    asyncio.Semaphore bilan parallel worker sonini cheklash.

    Misol:
        scraper = ParallelScraper(max_workers=3, headless=True)
        videos = await scraper.scrape(urls)
    """

    def __init__(self, max_workers: int = 3, headless: bool = True):
        self.max_workers = max_workers
        self.headless = headless

    async def scrape(self, urls: List[str]) -> List[Optional[Video]]:
        """
        URL ro'yxatini parallel scrape qilish.
        Natijalar tartib saqlanadi, None lar filtrlanadi.
        """
        if not urls:
            return []

        logger.info(
            f"Parallel scraping: {len(urls)} URL, "
            f"{self.max_workers} worker"
        )

        sem = asyncio.Semaphore(self.max_workers)

        async def limited(url, idx):
            async with sem:
                # Bir vaqtda bir nechta brauzer ochilmasligi uchun kichik delay
                await asyncio.sleep(idx * 0.5)
                return await _scrape_one(url, idx, self.headless)

        tasks = [limited(url, i + 1) for i, url in enumerate(urls)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        videos = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Task exception: {r}")
            elif r is not None:
                videos.append(r)

        logger.info(f"Parallel yakunlandi: {len(videos)}/{len(urls)} muvaffaqiyatli")
        return videos
