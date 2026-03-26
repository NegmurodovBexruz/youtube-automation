"""
Video sahifasidan metadata yig'ish — Playwright async
"""

import asyncio
import logging
import re
import random
from typing import Optional

from playwright.async_api import Page

from config import Config
from models.video import Video

logger = logging.getLogger(__name__)


def _parse_count(text: str) -> int:
    """'1,234,567 views' | '1.2M' | '12K' → int"""
    if not text:
        return 0
    text = text.strip().upper().replace(",", "").replace(" ", "")
    try:
        if "K" in text:
            num = re.search(r"[\d.]+", text)
            return int(float(num.group()) * 1_000) if num else 0
        if "M" in text:
            num = re.search(r"[\d.]+", text)
            return int(float(num.group()) * 1_000_000) if num else 0
        if "B" in text:
            num = re.search(r"[\d.]+", text)
            return int(float(num.group()) * 1_000_000_000) if num else 0
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else 0
    except (ValueError, AttributeError):
        return 0


def _duration_to_seconds(s: str) -> int:
    """'1:23:45' | '4:30' | '0:45' → soniya"""
    if not s:
        return 0
    parts = s.strip().split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return parts[0]
    except ValueError:
        return 0


def _video_id(url: str) -> str:
    m = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else ""


class VideoParser:
    """
    Playwright bilan YouTube video sahifasidan to'liq metadata yig'ish.
    """

    def __init__(self, page: Page):
        self.page = page

    async def parse_video(self, url: str) -> Optional[Video]:
        """
        URL bo'yicha Video obyektini to'ldirish.
        Xato bo'lsa MAX_RETRIES marta qayta urinadi.
        """
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                return await self._parse(url)
            except Exception as e:
                logger.warning(f"Parse urinish {attempt}/{Config.MAX_RETRIES} ({url[:60]}): {e}")
                if attempt < Config.MAX_RETRIES:
                    await asyncio.sleep(Config.RETRY_DELAY)
        logger.error(f"Video parse muvaffaqiyatsiz: {url}")
        return None

    async def _parse(self, url: str) -> Video:
        await self.page.goto(url, wait_until="domcontentloaded",
                             timeout=Config.BROWSER_TIMEOUT * 1000)

        # Sahifa to'liq yuklanishini kutish
        await asyncio.sleep(random.uniform(2.0, 3.0))

        # Description ni kengaytirish
        await self._expand_description()

        video = Video()
        video.video_url = url

        # Barcha maydonlarni parallel olish
        (
            video.video_title,
            video.view_count,
            video.like_count,
            video.channel_name,
            video.channel_subscribers,
            video.description,
            video.upload_date,
        ) = await asyncio.gather(
            self._get_title(),
            self._get_views(),
            self._get_likes(),
            self._get_channel_name(),
            self._get_subscribers(),
            self._get_description(),
            self._get_upload_date(),
        )

        video.duration        = await self._get_duration(url)
        video.duration_seconds = _duration_to_seconds(video.duration)
        video.video_type      = self._detect_type(url, video.duration_seconds)
        video.thumbnail_url   = self._thumbnail(url)

        logger.debug(
            f"✓ '{video.video_title[:45]}' | "
            f"views={video.view_count:,} | {video.video_type}"
        )
        return video

    # ── Maydon metodlari ──────────────────────────────────

    async def _get_title(self) -> str:
        selectors = [
            "h1.ytd-watch-metadata yt-formatted-string",
            "#title h1 yt-formatted-string",
            "h1.title yt-formatted-string",
        ]
        for sel in selectors:
            try:
                el = self.page.locator(sel).first
                text = await el.inner_text(timeout=5000)
                if text and text.strip():
                    return text.strip()
            except Exception:
                continue
        # Fallback: page title
        title = await self.page.title()
        return title.replace(" - YouTube", "").strip()

    async def _get_views(self) -> int:
        selectors = [
            "span.view-count",
            "ytd-video-view-count-renderer span.view-count",
        ]
        for sel in selectors:
            try:
                text = await self.page.locator(sel).first.inner_text(timeout=5000)
                if text:
                    return _parse_count(text)
            except Exception:
                continue
        return 0

    async def _get_likes(self) -> int:
        # Eng ishonchli: like tugmasi aria-label
        try:
            btn = self.page.locator(
                'button[aria-label*="like"]:not([aria-label*="dislike"])'
            ).first
            aria = await btn.get_attribute("aria-label", timeout=5000)
            if aria:
                m = re.search(r"[\d,]+", aria)
                if m:
                    return _parse_count(m.group())
        except Exception:
            pass
        return 0

    async def _get_channel_name(self) -> str:
        selectors = [
            "#channel-name yt-formatted-string",
            "ytd-channel-name yt-formatted-string a",
            "#owner-name a",
        ]
        for sel in selectors:
            try:
                text = await self.page.locator(sel).first.inner_text(timeout=5000)
                if text and text.strip():
                    return text.strip()
            except Exception:
                continue
        return ""

    async def _get_subscribers(self) -> str:
        selectors = [
            "#owner-sub-count",
            "ytd-video-owner-renderer #subscriber-count",
        ]
        for sel in selectors:
            try:
                text = await self.page.locator(sel).first.inner_text(timeout=5000)
                if text and text.strip():
                    return text.strip()
            except Exception:
                continue
        return ""

    async def _expand_description(self):
        """'Show more' tugmasini bosib descriptionni ochish"""
        try:
            btn = self.page.locator(
                "tp-yt-paper-button#expand, ytd-text-inline-expander #expand"
            ).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await asyncio.sleep(0.5)
        except Exception:
            pass

    async def _get_description(self) -> str:
        selectors = [
            "#description-inner yt-attributed-string",
            "#description ytd-text-inline-expander",
            "ytd-text-inline-expander yt-attributed-string",
            "#description-inline-expander",
        ]
        for sel in selectors:
            try:
                text = await self.page.locator(sel).first.inner_text(timeout=5000)
                if text and len(text.strip()) > 5:
                    return text.strip()[:5000]
            except Exception:
                continue
        return ""

    async def _get_upload_date(self) -> str:
        months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
        try:
            els = await self.page.locator(
                "#info-strings yt-formatted-string"
            ).all()
            for el in els:
                text = await el.inner_text(timeout=3000)
                text = text.strip()
                if any(m in text for m in months) or any(
                    y in text for y in ["2022","2023","2024","2025","2026"]
                ):
                    return text
        except Exception:
            pass
        return ""

    async def _get_duration(self, url: str) -> str:
        # Shorts
        if "/shorts/" in url:
            try:
                dur = await self.page.evaluate(
                    "document.querySelector('video')?.duration"
                )
                if dur:
                    s = int(float(dur))
                    return f"0:{s:02d}"
            except Exception:
                pass
            return "0:30"

        # meta[itemprop=duration] — PT1H2M3S
        try:
            content = await self.page.locator(
                'meta[itemprop="duration"]'
            ).first.get_attribute("content", timeout=5000)
            if content:
                h = int((re.search(r"(\d+)H", content) or [0, 0])[1] or 0)
                m = int((re.search(r"(\d+)M", content) or [0, 0])[1] or 0)
                s = int((re.search(r"(\d+)S", content) or [0, 0])[1] or 0)
                if h:
                    return f"{h}:{m:02d}:{s:02d}"
                return f"{m}:{s:02d}"
        except Exception:
            pass

        # Playbar dagi vaqt
        try:
            text = await self.page.locator(
                ".ytp-time-duration"
            ).first.inner_text(timeout=5000)
            if text and text.strip():
                return text.strip()
        except Exception:
            pass

        return ""

    def _thumbnail(self, url: str) -> str:
        vid = _video_id(url)
        return f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg" if vid else ""

    def _detect_type(self, url: str, duration_sec: int) -> str:
        if "/shorts/" in url:
            return "shorts"
        if 0 < duration_sec <= Config.SHORTS_MAX_DURATION_SEC:
            return "shorts"
        return "standard"
