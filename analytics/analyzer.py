"""
Video ma'lumotlarini tahlil qilish moduli
"""

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from models.video import Video

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """
    10 ta video bo'yicha statistik tahlil.
    """

    def __init__(self, videos: List[Video]):
        self.videos = videos

    def analyze(self) -> Dict[str, Any]:
        """
        Barcha tahlillarni bajarib, natija dict qaytaradi.

        """
        if not self.videos:
            logger.warning("Tahlil uchun video yo'q")
            return {}

        logger.info(f"{len(self.videos)} ta video tahlil qilinmoqda...")

        analytics = {
            "total_videos": len(self.videos),
            "views": self._views_stats(),
            "likes": self._likes_stats(),
            "video_types": self._video_type_stats(),
            "channels": self._channel_stats(),
            "duration": self._duration_stats(),
            "top_comments": self._top_comments_global(),
            "summary": self._summary(),
        }

        logger.info("Tahlil yakunlandi")
        return analytics

    # ──────────────────────────────────────────────────────
    # Ko'rishlar statistikasi
    # ──────────────────────────────────────────────────────

    def _views_stats(self) -> Dict[str, Any]:
        views = [v.view_count for v in self.videos if v.view_count > 0]
        if not views:
            return {}

        most_viewed = max(self.videos, key=lambda v: v.view_count)
        least_viewed = min(self.videos, key=lambda v: v.view_count)

        return {
            "average": int(sum(views) / len(views)),
            "total": sum(views),
            "max": most_viewed.view_count,
            "min": least_viewed.view_count,
            "most_viewed_title": most_viewed.video_title,
            "most_viewed_url": most_viewed.video_url,
            "least_viewed_title": least_viewed.video_title,
            "least_viewed_url": least_viewed.video_url,
        }

    # ──────────────────────────────────────────────────────
    # Like statistikasi
    # ──────────────────────────────────────────────────────

    def _likes_stats(self) -> Dict[str, Any]:
        videos_with_likes = [v for v in self.videos if v.like_count > 0]
        if not videos_with_likes:
            return {}

        most_liked = max(videos_with_likes, key=lambda v: v.like_count)
        total = sum(v.like_count for v in videos_with_likes)

        return {
            "total": total,
            "average": int(total / len(videos_with_likes)),
            "max": most_liked.like_count,
            "most_liked_title": most_liked.video_title,
            "most_liked_url": most_liked.video_url,
        }

    # ──────────────────────────────────────────────────────
    # Video turi (Shorts vs Standard)
    # ──────────────────────────────────────────────────────

    def _video_type_stats(self) -> Dict[str, Any]:
        shorts_count = sum(1 for v in self.videos if v.video_type == "shorts")
        standard_count = len(self.videos) - shorts_count
        total = len(self.videos)

        return {
            "shorts": shorts_count,
            "standard": standard_count,
            "shorts_percent": round(shorts_count / total * 100, 1) if total else 0,
            "standard_percent": round(standard_count / total * 100, 1) if total else 0,
            "ratio": f"{shorts_count} Shorts / {standard_count} Standard",
        }

    # ──────────────────────────────────────────────────────
    # Kanal statistikasi
    # ──────────────────────────────────────────────────────

    def _channel_stats(self) -> Dict[str, Any]:
        channels = [v.channel_name for v in self.videos if v.channel_name]
        if not channels:
            return {}

        counter = Counter(channels)
        most_active_channel, most_active_count = counter.most_common(1)[0]

        unique_channels = len(counter)
        top_channels = [
            {"channel": ch, "video_count": cnt}
            for ch, cnt in counter.most_common(5)
        ]

        return {
            "unique_channels": unique_channels,
            "most_active_channel": most_active_channel,
            "most_active_count": most_active_count,
            "top_channels": top_channels,
        }

    # ──────────────────────────────────────────────────────
    # Davomiylik statistikasi
    # ──────────────────────────────────────────────────────

    def _duration_stats(self) -> Dict[str, Any]:
        durations = [v.duration_seconds for v in self.videos if v.duration_seconds > 0]
        if not durations:
            return {}

        avg_sec = int(sum(durations) / len(durations))
        longest = max(self.videos, key=lambda v: v.duration_seconds)
        shortest = min(
            [v for v in self.videos if v.duration_seconds > 0],
            key=lambda v: v.duration_seconds,
        )

        return {
            "average_seconds": avg_sec,
            "average_formatted": self._format_seconds(avg_sec),
            "longest_title": longest.video_title,
            "longest_duration": longest.duration,
            "shortest_title": shortest.video_title,
            "shortest_duration": shortest.duration,
        }

    # ──────────────────────────────────────────────────────
    # Global top kommentlar
    # ──────────────────────────────────────────────────────

    def _top_comments_global(self) -> List[Dict]:
        """Barcha videolardan eng ko'p like olgan 3 ta komment"""
        all_comments = []
        for video in self.videos:
            for comment in video.top_comments:
                all_comments.append({
                    "author": comment.author,
                    "text": comment.text,
                    "likes": comment.likes,
                    "date": comment.date,
                    "video_title": video.video_title,
                    "video_url": video.video_url,
                })

        top3 = sorted(all_comments, key=lambda c: c["likes"], reverse=True)[:3]
        return top3

    # ──────────────────────────────────────────────────────
    # Qisqacha xulosa
    # ──────────────────────────────────────────────────────

    def _summary(self) -> Dict[str, Any]:
        """Terminal uchun qisqacha xulosa"""
        views = self._views_stats()
        likes = self._likes_stats()
        types = self._video_type_stats()
        channels = self._channel_stats()

        return {
            "total_videos_analyzed": len(self.videos),
            "average_views": views.get("average", 0),
            "most_popular_video": views.get("most_viewed_title", "N/A"),
            "most_liked_video": likes.get("most_liked_title", "N/A"),
            "shorts_vs_standard": types.get("ratio", "N/A"),
            "most_active_channel": channels.get("most_active_channel", "N/A"),
        }

    @staticmethod
    def _format_seconds(seconds: int) -> str:
        """1234 -> '20:34'"""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
