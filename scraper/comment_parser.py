"""
YouTube kommentlarini yig'ish — Playwright async
"""

import asyncio
import logging
import re
from typing import List

from playwright.async_api import Page

from config import Config
from models.video import Comment

logger = logging.getLogger(__name__)


def _parse_likes(raw: str) -> int:
    if not raw or not raw.strip():
        return 0
    raw = raw.strip().upper().replace(",", "")
    try:
        if "K" in raw:
            return int(float(raw.replace("K", "")) * 1000)
        if "M" in raw:
            return int(float(raw.replace("M", "")) * 1_000_000)
        digits = re.sub(r"[^\d]", "", raw)
        return int(digits) if digits else 0
    except ValueError:
        return 0


class CommentParser:
    """
    Playwright bilan YouTube kommentlarini yig'ish.
    Kommentlar lazy-load — scroll kerak.
    """

    def __init__(self, page: Page):
        self.page = page

    async def get_top_comments(
        self, max_comments: int = 10
    ) -> List[Comment]:
        """
        Joriy sahifadagi kommentlarni olish.
        (Sahifa avval ochilgan bo'lishi kerak.)
        """
        logger.info(f"Kommentlar yig'ilmoqda (max: {max_comments})...")

        await self._scroll_to_comments()

        # Kommentlar yuklanguncha urinish
        for attempt in range(Config.MAX_SCROLL_ATTEMPTS):
            count = await self.page.locator(
                "ytd-comment-thread-renderer"
            ).count()
            if count >= max_comments:
                break
            await self._scroll_down()
            await asyncio.sleep(Config.SCROLL_PAUSE)

        comments = []
        try:
            threads = await self.page.locator(
                "ytd-comment-thread-renderer"
            ).all()
            logger.info(f"{len(threads)} ta komment topildi")

            for thread in threads[:max_comments]:
                comment = await self._parse_thread(thread)
                if comment:
                    comments.append(comment)

        except Exception as e:
            logger.error(f"Kommentlar xato: {e}")

        logger.info(f"{len(comments)} ta komment muvaffaqiyatli olindi")
        return comments

    async def _scroll_to_comments(self):
        """Kommentlar bo'limiga scroll qilish"""
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.45)")
        await asyncio.sleep(2)
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.65)")
        await asyncio.sleep(2)

    async def _scroll_down(self):
        await self.page.evaluate("window.scrollBy(0, 800)")

    async def _parse_thread(self, thread) -> Comment:
        """Bitta komment elementini parse qilish"""
        try:
            author = await self._safe_text(thread, "#author-text span")
            text   = await self._safe_text(thread, "#content-text")
            likes  = await self._safe_text(thread, "#vote-count-middle")
            date   = await self._safe_date(thread)

            return Comment(
                author=author,
                text=text,
                likes=_parse_likes(likes),
                date=date,
            )
        except Exception as e:
            logger.debug(f"Komment parse xato: {e}")
            return None

    async def _safe_text(self, parent, selector: str) -> str:
        try:
            el = parent.locator(selector).first
            text = await el.inner_text(timeout=3000)
            return text.strip()
        except Exception:
            return ""

    async def _safe_date(self, parent) -> str:
        try:
            links = await parent.locator("a.yt-simple-endpoint").all()
            for link in links:
                href = await link.get_attribute("href") or ""
                if "lc=" in href or "comment" in href:
                    spans = await link.locator("span").all()
                    for span in spans:
                        txt = (await span.inner_text()).strip()
                        if txt and any(
                            w in txt for w in
                            ["ago", "year", "month", "day", "hour", "week"]
                        ):
                            return txt
        except Exception:
            pass
        return ""
