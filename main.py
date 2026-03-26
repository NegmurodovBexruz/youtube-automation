"""
YouTube Web Automation Tool — CLI entry point (Playwright async)
"""

import argparse
import asyncio
import uuid
import logging
import sys
from pathlib import Path

from config import Config
from scraper.browser import BrowserManager
from scraper.search import YouTubeSearch
from scraper.video_parser import VideoParser
from scraper.comment_parser import CommentParser
from scraper.parallel_scraper import ParallelScraper
from analytics.analyzer import VideoAnalyzer
from utils.storage import DataStorage
from utils.reporter import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("automation.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="YouTube Automation Tool (Playwright)")
    parser.add_argument("--query",      type=str,   default="you tube")
    parser.add_argument("--headless",   action="store_true", default=True)
    parser.add_argument("--no-headless",action="store_true", default=False)
    parser.add_argument("--output-dir", type=str,   default="output")
    parser.add_argument("--max-videos", type=int,   default=10)
    parser.add_argument("--format",     choices=["json","csv","both"], default="both")
    parser.add_argument("--parallel",   action="store_true", default=False)
    parser.add_argument("--workers",    type=int,   default=3)
    return parser.parse_args()


async def main():
    args = parse_args()
    headless = not args.no_headless

    Config.MAX_VIDEOS = args.max_videos

    job_id = str(uuid.uuid4())[:8]
    out_dir = f"{args.output_dir}/{job_id}"
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("YouTube Automation (Playwright) ishga tushdi")
    logger.info(f"Query     : '{args.query}'")
    logger.info(f"Headless  : {headless}")
    logger.info(f"Parallel  : {args.parallel}" + (f" ({args.workers} workers)" if args.parallel else ""))
    logger.info("=" * 60)

    # ── 1. Qidirish
    video_urls = []
    async with BrowserManager(headless=headless) as bm:
        page = await bm.new_page()
        searcher = YouTubeSearch(page)
        video_urls = await searcher.search_and_get_urls(args.query, args.max_videos)

    if not video_urls:
        logger.error("Video URL topilmadi!")
        return

    logger.info(f"{len(video_urls)} ta URL topildi")

    # ── 2. Scraping
    videos = []

    if args.parallel:
        scraper = ParallelScraper(max_workers=args.workers, headless=headless)
        videos = await scraper.scrape(video_urls)
    else:
        async with BrowserManager(headless=headless) as bm:
            page = await bm.new_page()
            vp = VideoParser(page)
            cp = CommentParser(page)

            for i, url in enumerate(video_urls, 1):
                logger.info(f"\nVideo {i}/{len(video_urls)}: {url[:60]}")
                try:
                    video = await vp.parse_video(url)
                    if video:
                        video.top_comments = await cp.get_top_comments(
                            max_comments=Config.MAX_COMMENTS
                        )
                        videos.append(video)
                        logger.info(f"✓ {video.video_title[:50]}")
                    # Rate limiting
                    await asyncio.sleep(Config.get_random_delay())
                except Exception as e:
                    logger.error(f"Xato: {e}")
                    continue

    if not videos:
        logger.error("Hech qanday video olinmadi!")
        return

    logger.info(f"\n{len(videos)} ta video yig'ildi")

    # ── 3. Saqlash
    storage = DataStorage(output_dir=out_dir)
    if args.format in ("json", "both"):
        logger.info(f"JSON: {storage.save_json(videos)}")
    if args.format in ("csv", "both"):
        logger.info(f"CSV : {storage.save_csv(videos)}")

    # ── 4. Tahlil
    analytics = VideoAnalyzer(videos).analyze()
    logger.info(f"Analytics: {storage.save_analytics(analytics)}")

    # ── 5. Hisobot
    reporter = ReportGenerator(videos, analytics, output_dir=out_dir)
    report = reporter.generate_html_report()
    logger.info(f"Hisobot: {report}")
    reporter.print_summary()

    logger.info("\n✅ Yakunlandi!")


if __name__ == "__main__":
    asyncio.run(main())
