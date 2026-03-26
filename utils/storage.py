"""
Ma'lumotlarni saqlash — JSON, CSV, PostgreSQL
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from models.video import Video

logger = logging.getLogger(__name__)


class DataStorage:
    """
    JSON, CSV va PostgreSQL ga saqlash.
    DB instance ixtiyoriy — yo'q bo'lsa faqat fayllarga yozadi.
    """

    def __init__(self, output_dir: str = "output", db=None):
        """
        Args:
            output_dir: JSON/CSV saqlanadigan papka
            db: Database instance (ixtiyoriy)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db = db  # utils.database.Database | None

    # ── JSON

    def save_json(self, videos: List[Video], filename: str = "output.json") -> str:
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in videos], f, ensure_ascii=False, indent=2)
        logger.info(f"JSON: {path}")
        return str(path)

    # ── CSV

    def save_csv(self, videos: List[Video], filename: str = "output.csv") -> str:
        path = self.output_dir / filename
        fields = [
            "video_title", "video_url", "duration", "view_count",
            "like_count", "channel_name", "channel_subscribers",
            "video_type", "upload_date", "thumbnail_url",
            "duration_seconds", "description",
        ]
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for v in videos:
                writer.writerow({field: getattr(v, field, "") for field in fields})
        logger.info(f"CSV: {path}")
        return str(path)

    # ── Analytics JSON

    def save_analytics(self, analytics: Dict[str, Any],
                       filename: str = "analytics.json") -> str:
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(analytics, f, ensure_ascii=False, indent=2)
        logger.info(f"Analytics JSON: {path}")
        return str(path)

    # ── PostgreSQL

    async def save_to_db(self, job_id: str, videos: List[Video],
                         analytics: Dict[str, Any]) -> bool:
        """
        Videolar va analyticsni PostgreSQL ga saqlash.
        db inject qilinmagan bo'lsa — o'tkazib yuboradi.
        """
        if not self.db:
            logger.debug("DB yo'q — PostgreSQL saqlash o'tkazildi")
            return False

        try:
            await self.db.save_videos(job_id, videos)
            await self.db.save_analytics(job_id, analytics)
            logger.info(f"PostgreSQL ga saqlandi ✓ (job: {job_id})")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL saqlashda xato: {e}")
            return False
