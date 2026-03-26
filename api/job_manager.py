"""
Job Manager — Playwright native async + PostgreSQL
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from config import Config
from models.video import Video
from analytics.analyzer import VideoAnalyzer
from utils.storage import DataStorage
from utils.reporter import ReportGenerator

logger = logging.getLogger(__name__)


class JobStatus:
    PENDING   = "pending"
    SEARCHING = "searching"
    SCRAPING  = "scraping"
    ANALYZING = "analyzing"
    DONE      = "done"
    ERROR     = "error"


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def get_job(self, job_id: str) -> Optional[Dict]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[Dict]:
        return [
            {k: v for k, v in j.items() if k != "videos"}
            for j in self._jobs.values()
        ]

    def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    def active_count(self) -> int:
        return sum(
            1 for j in self._jobs.values()
            if j["status"] not in (JobStatus.DONE, JobStatus.ERROR)
        )

    async def cleanup(self):
        pass

    # ── Job ishga tushirish

    async def run_job(self, job_id: str, req, ws_manager, db=None):
        """
        Args:
            job_id:     Unikal job ID
            req:        ScrapeRequest (FastAPI Pydantic model)
            ws_manager: WebSocketManager
            db:         Database instance (ixtiyoriy)
        """
        self._jobs[job_id] = {
            "job_id":       job_id,
            "query":        req.query,
            "status":       JobStatus.PENDING,
            "progress":     0,
            "total_videos": req.max_videos,
            "videos_done":  0,
            "started_at":   time.time(),
            "finished_at":  None,
            "error":        None,
            "videos":       [],
            "analytics":    {},
            "report_url":   None,
        }

        try:
            # ── 1. Qidirish
            await self._emit(job_id, ws_manager,
                             status=JobStatus.SEARCHING,
                             log=f"'{req.query}' qidirilmoqda...")

            urls = await self._search(req)
            if not urls:
                raise RuntimeError("Hech qanday URL topilmadi")

            await self._emit(job_id, ws_manager,
                             log=f"{len(urls)} ta URL topildi",
                             extra={"found_urls": len(urls)})

            # ── 2. Scraping
            await self._emit(job_id, ws_manager,
                             status=JobStatus.SCRAPING,
                             log="Video ma'lumotlari yig'ilmoqda...")

            if req.parallel:
                await self._emit(job_id, ws_manager,
                                 log=f"Parallel rejim: {req.workers} worker")
                videos = await self._scrape_parallel(job_id, urls, req, ws_manager)
            else:
                videos = await self._scrape_sequential(job_id, urls, req, ws_manager)

            self._jobs[job_id]["videos"] = [v.to_dict() for v in videos]

            # ── 3. Tahlil
            await self._emit(job_id, ws_manager,
                             status=JobStatus.ANALYZING,
                             log="Tahlil qilinmoqda...")
            analytics = VideoAnalyzer(videos).analyze()
            self._jobs[job_id]["analytics"] = analytics

            # ── 4. Saqlash
            out_dir = f"output/{job_id}"
            storage = DataStorage(output_dir=out_dir, db=db)

            # JSON / CSV
            if req.save_format in ("json", "both", "all"):
                storage.save_json(videos)
            if req.save_format in ("csv", "both", "all"):
                storage.save_csv(videos)
            storage.save_analytics(analytics)

            # PostgreSQL
            if db and req.save_format in ("db", "all", "both"):
                await storage.save_to_db(job_id, videos, analytics)
                try:
                    await db.update_job_status(
                        job_id, JobStatus.DONE, finished=True
                    )
                except Exception:
                    pass

            # HTML hisobot
            ReportGenerator(videos, analytics, out_dir).generate_html_report()
            self._jobs[job_id]["report_url"] = f"/output/{job_id}/report.html"
            self._jobs[job_id]["finished_at"] = time.time()

            # ── 5. Done
            elapsed = round(time.time() - self._jobs[job_id]["started_at"], 1)
            await self._emit(
                job_id, ws_manager,
                status=JobStatus.DONE,
                progress=100,
                log=f"✅ Yakunlandi! {len(videos)} ta video, {elapsed}s",
                ws_type="done",
                extra={
                    "videos":     self._jobs[job_id]["videos"],
                    "analytics":  analytics,
                    "report_url": self._jobs[job_id]["report_url"],
                    "elapsed_sec": elapsed,
                    "total": len(videos),
                },
            )

        except Exception as e:
            logger.error(f"Job {job_id} xato: {e}", exc_info=True)
            self._jobs[job_id].update({"status": JobStatus.ERROR, "error": str(e)})
            if db:
                try:
                    await db.update_job_status(job_id, JobStatus.ERROR, error=str(e))
                except Exception:
                    pass
            await ws_manager.send(job_id, {
                "type": "error", "job_id": job_id, "message": str(e)
            })

    # ── Helpers

    async def _search(self, req) -> List[str]:
        from scraper.browser import BrowserManager
        from scraper.search import YouTubeSearch
        async with BrowserManager(headless=req.headless) as bm:
            page = await bm.new_page()
            return await YouTubeSearch(page).search_and_get_urls(
                req.query, req.max_videos
            )

    async def _scrape_one(self, url: str, headless: bool) -> Optional[Video]:
        from scraper.browser import BrowserManager
        from scraper.video_parser import VideoParser
        from scraper.comment_parser import CommentParser
        async with BrowserManager(headless=headless) as bm:
            page = await bm.new_page()
            video = await VideoParser(page).parse_video(url)
            if video:
                video.top_comments = await CommentParser(page).get_top_comments(
                    max_comments=Config.MAX_COMMENTS
                )
            return video

    async def _scrape_sequential(self, job_id, urls, req, ws_manager) -> List[Video]:
        from scraper.browser import BrowserManager
        from scraper.video_parser import VideoParser
        from scraper.comment_parser import CommentParser

        videos = []
        total = len(urls)

        async with BrowserManager(headless=req.headless) as bm:
            page = await bm.new_page()
            vp = VideoParser(page)
            cp = CommentParser(page)

            for idx, url in enumerate(urls, 1):
                pct = round(idx / total * 100)
                await ws_manager.send(job_id, {
                    "type": "progress", "job_id": job_id,
                    "current": idx, "total": total, "percent": pct,
                    "message": f"Video {idx}/{total}...",
                })
                try:
                    video = await vp.parse_video(url)
                    if video:
                        video.top_comments = await cp.get_top_comments(
                            max_comments=Config.MAX_COMMENTS
                        )
                        videos.append(video)
                        self._jobs[job_id]["videos_done"] += 1
                        self._jobs[job_id]["progress"] = pct
                        await ws_manager.send(job_id, {
                            "type": "video_done", "job_id": job_id,
                            "current": idx, "total": total, "percent": pct,
                            "video": self._video_payload(video),
                        })
                    else:
                        await ws_manager.send(job_id, {
                            "type": "video_error", "job_id": job_id,
                            "current": idx, "total": total, "url": url,
                        })
                except Exception as e:
                    logger.error(f"Video xato [{idx}]: {e}")
                    await ws_manager.send(job_id, {
                        "type": "video_error", "job_id": job_id,
                        "current": idx, "total": total, "url": url, "message": str(e),
                    })
                await asyncio.sleep(Config.get_random_delay())

        return videos

    async def _scrape_parallel(self, job_id, urls, req, ws_manager) -> List[Video]:
        total = len(urls)
        done_count = 0
        videos = []
        sem = asyncio.Semaphore(req.workers)

        async def one(url, idx):
            nonlocal done_count
            async with sem:
                await asyncio.sleep(idx * 0.3)
                try:
                    video = await self._scrape_one(url, req.headless)
                except Exception as e:
                    logger.error(f"Parallel [{idx}]: {e}")
                    video = None

            done_count += 1
            pct = round(done_count / total * 100)
            self._jobs[job_id]["progress"] = pct

            if video:
                videos.append(video)
                self._jobs[job_id]["videos_done"] += 1
                await ws_manager.send(job_id, {
                    "type": "video_done", "job_id": job_id,
                    "current": done_count, "total": total, "percent": pct,
                    "video": self._video_payload(video),
                })
            else:
                await ws_manager.send(job_id, {
                    "type": "video_error", "job_id": job_id,
                    "current": done_count, "total": total, "url": url,
                })

        await asyncio.gather(*[one(url, i+1) for i, url in enumerate(urls)])
        return videos

    @staticmethod
    def _video_payload(v: Video) -> dict:
        return {
            "title":      v.video_title,
            "url":        v.video_url,
            "thumbnail":  v.thumbnail_url,
            "channel":    v.channel_name,
            "views":      v.view_count,
            "likes":      v.like_count,
            "duration":   v.duration,
            "video_type": v.video_type,
            "upload_date":v.upload_date,
        }

    async def _emit(self, job_id, ws_manager, status=None,
                    progress=None, log=None, extra=None, ws_type="log"):
        job = self._jobs[job_id]
        if status:   job["status"] = status
        if progress is not None: job["progress"] = progress

        payload = {"type": ws_type, "job_id": job_id}
        if log:      payload["message"] = log;   logger.info(f"[{job_id}] {log}")
        if status:   payload["status"]  = status
        if progress is not None: payload["percent"] = progress
        if extra:    payload.update(extra)

        await ws_manager.send(job_id, payload)
