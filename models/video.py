"""
Video ma'lumotlari modeli
"""

from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class Comment:
    """Bitta komment ma'lumotlari"""
    author: str = ""
    text: str = ""
    likes: int = 0
    date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Video:
    """Bitta YouTube video ma'lumotlari"""
    video_title: str = ""
    video_url: str = ""
    duration: str = ""             # "MM:SS" yoki "H:MM:SS" formatda
    duration_seconds: int = 0      # Soniyalarda (hisoblash uchun)
    view_count: int = 0
    like_count: int = 0
    channel_name: str = ""
    channel_subscribers: str = ""
    description: str = ""
    video_type: str = "standard"   # "shorts" yoki "standard"
    top_comments: List[Comment] = field(default_factory=list)
    thumbnail_url: str = ""
    upload_date: str = ""

    def to_dict(self) -> dict:
        """Serializatsiya qilish uchun dict ga aylantirish"""
        data = asdict(self)
        return data

    @property
    def is_shorts(self) -> bool:
        return self.video_type == "shorts"

    def __repr__(self) -> str:
        return (
            f"Video(title='{self.video_title[:40]}...', "
            f"views={self.view_count:,}, "
            f"type={self.video_type})"
        )
