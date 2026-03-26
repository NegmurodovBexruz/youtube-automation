"""
PostgreSQL — SQLAlchemy async ORM + asyncpg
Jadvallar, CRUD operatsiyalar
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger, Column, DateTime, ForeignKey,
    Integer, String, Text, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship

from config import Config

logger = logging.getLogger(__name__)


# ── Base

class Base(DeclarativeBase):
    pass


# ── Modellar

class JobModel(Base):
    """Scraping job — qidiruv tarixi"""
    __tablename__ = "jobs"

    id          = Column(String(8),   primary_key=True)
    query       = Column(String(255), nullable=False)
    status      = Column(String(20),  nullable=False, default="pending")
    max_videos  = Column(Integer,     default=10)
    headless    = Column(String(5),   default="true")
    parallel    = Column(String(5),   default="false")
    started_at  = Column(DateTime,    default=datetime.utcnow)
    finished_at = Column(DateTime,    nullable=True)
    error       = Column(Text,        nullable=True)

    videos      = relationship("VideoModel",    back_populates="job", cascade="all, delete-orphan")
    analytics   = relationship("AnalyticsModel", back_populates="job", uselist=False, cascade="all, delete-orphan")


class VideoModel(Base):
    """Video ma'lumotlari"""
    __tablename__ = "videos"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    job_id              = Column(String(8), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    video_title         = Column(String(500),  default="")
    video_url           = Column(String(500),  nullable=False)
    duration            = Column(String(20),   default="")
    duration_seconds    = Column(Integer,      default=0)
    view_count          = Column(BigInteger,   default=0)
    like_count          = Column(BigInteger,   default=0)
    channel_name        = Column(String(255),  default="")
    channel_subscribers = Column(String(100),  default="")
    description         = Column(Text,         default="")
    video_type          = Column(String(20),   default="standard")
    thumbnail_url       = Column(String(500),  default="")
    upload_date         = Column(String(100),  default="")
    created_at          = Column(DateTime,     default=datetime.utcnow)

    job      = relationship("JobModel",     back_populates="videos")
    comments = relationship("CommentModel", back_populates="video", cascade="all, delete-orphan")


class CommentModel(Base):
    """Kommentlar"""
    __tablename__ = "comments"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    video_id   = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    author     = Column(String(255), default="")
    text       = Column(Text,        default="")
    likes      = Column(Integer,     default=0)
    date       = Column(String(100), default="")
    created_at = Column(DateTime,    default=datetime.utcnow)

    video = relationship("VideoModel", back_populates="comments")


class AnalyticsModel(Base):
    """Job tahlil natijalari — JSONB da saqlanadi"""
    __tablename__ = "analytics"

    id         = Column(Integer,    primary_key=True, autoincrement=True)
    job_id     = Column(String(8),  ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    data       = Column(JSONB,      nullable=False, default=dict)
    created_at = Column(DateTime,   default=datetime.utcnow)

    job = relationship("JobModel", back_populates="analytics")


# ── Engine & Session

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            Config.DATABASE_URL,
            echo=False,           # True qilsang SQL logga chiqadi
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,   # ulanish tirik ekanini tekshiradi
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db():
    """Barcha jadvallarni yaratish (agar mavjud bo'lmasa)"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL jadvallar tayyor ✓")


async def close_db():
    """Engine ni yopish"""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


# ── CRUD

class Database:
    """
    Barcha DB operatsiyalari shu classda.

    """

    def __init__(self):
        self.factory = get_session_factory()

    # ── Job

    async def create_job(self, job_id: str, query: str,
                         max_videos: int = 10, headless: bool = True,
                         parallel: bool = False) -> JobModel:
        async with self.factory() as session:
            job = JobModel(
                id=job_id, query=query,
                status="pending", max_videos=max_videos,
                headless=str(headless).lower(),
                parallel=str(parallel).lower(),
            )
            session.add(job)
            await session.commit()
            logger.info(f"Job yaratildi: {job_id}")
            return job

    async def update_job_status(self, job_id: str, status: str,
                                error: str = None, finished: bool = False):
        async with self.factory() as session:
            job = await session.get(JobModel, job_id)
            if job:
                job.status = status
                if error:
                    job.error = error
                if finished:
                    job.finished_at = datetime.utcnow()
                await session.commit()

    async def get_job(self, job_id: str) -> Optional[Dict]:
        async with self.factory() as session:
            job = await session.get(JobModel, job_id)
            if not job:
                return None
            return {
                "job_id":      job.id,
                "query":       job.query,
                "status":      job.status,
                "started_at":  str(job.started_at),
                "finished_at": str(job.finished_at) if job.finished_at else None,
                "error":       job.error,
            }

    async def list_jobs(self) -> List[Dict]:
        from sqlalchemy import select
        async with self.factory() as session:
            result = await session.execute(
                select(JobModel).order_by(JobModel.started_at.desc()).limit(50)
            )
            jobs = result.scalars().all()
            return [
                {
                    "job_id":  j.id,
                    "query":   j.query,
                    "status":  j.status,
                    "started_at": str(j.started_at),
                }
                for j in jobs
            ]

    # ── Videos

    async def save_videos(self, job_id: str, videos: List[Any]) -> List[int]:
        """
        Video ro'yxatini DB ga saqlash.
        videos: Video dataclass obyektlari ro'yxati
        Qaytaradi: yangi video ID lar
        """
        video_ids = []
        async with self.factory() as session:
            for v in videos:
                vm = VideoModel(
                    job_id=job_id,
                    video_title=v.video_title,
                    video_url=v.video_url,
                    duration=v.duration,
                    duration_seconds=v.duration_seconds,
                    view_count=v.view_count,
                    like_count=v.like_count,
                    channel_name=v.channel_name,
                    channel_subscribers=v.channel_subscribers,
                    description=v.description,
                    video_type=v.video_type,
                    thumbnail_url=v.thumbnail_url,
                    upload_date=v.upload_date,
                )
                session.add(vm)
                await session.flush()  # ID olish uchun

                # Kommentlarni ham saqlash
                for c in (v.top_comments or []):
                    cm = CommentModel(
                        video_id=vm.id,
                        author=c.author,
                        text=c.text,
                        likes=c.likes,
                        date=c.date,
                    )
                    session.add(cm)

                video_ids.append(vm.id)

            await session.commit()
        logger.info(f"DB ga {len(video_ids)} ta video saqlandi (job: {job_id})")
        return video_ids

    async def get_videos(self, job_id: str) -> List[Dict]:
        """Job bo'yicha barcha videolar (kommentlar bilan)"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with self.factory() as session:
            result = await session.execute(
                select(VideoModel)
                .where(VideoModel.job_id == job_id)
                .options(selectinload(VideoModel.comments))
                .order_by(VideoModel.id)
            )
            videos = result.scalars().all()
            return [self._video_to_dict(v) for v in videos]

    # ── Analytics

    async def save_analytics(self, job_id: str, data: Dict):
        async with self.factory() as session:
            am = AnalyticsModel(job_id=job_id, data=data)
            session.add(am)
            await session.commit()
        logger.info(f"Analytics saqlandi (job: {job_id})")

    async def get_analytics(self, job_id: str) -> Optional[Dict]:
        from sqlalchemy import select
        async with self.factory() as session:
            result = await session.execute(
                select(AnalyticsModel).where(AnalyticsModel.job_id == job_id)
            )
            am = result.scalar_one_or_none()
            return am.data if am else None

    # ── Stats

    async def get_global_stats(self) -> Dict:
        """Umumiy statistika"""
        async with self.factory() as session:
            total_jobs = await session.scalar(
                text("SELECT COUNT(*) FROM jobs")
            )
            total_videos = await session.scalar(
                text("SELECT COUNT(*) FROM videos")
            )
            total_comments = await session.scalar(
                text("SELECT COUNT(*) FROM comments")
            )
            avg_views = await session.scalar(
                text("SELECT AVG(view_count) FROM videos WHERE view_count > 0")
            )
            return {
                "total_jobs":     total_jobs or 0,
                "total_videos":   total_videos or 0,
                "total_comments": total_comments or 0,
                "avg_views":      int(avg_views or 0),
            }

    # ── Helper

    @staticmethod
    def _video_to_dict(v: VideoModel) -> Dict:
        return {
            "id":                 v.id,
            "video_title":        v.video_title,
            "video_url":          v.video_url,
            "duration":           v.duration,
            "duration_seconds":   v.duration_seconds,
            "view_count":         v.view_count,
            "like_count":         v.like_count,
            "channel_name":       v.channel_name,
            "channel_subscribers":v.channel_subscribers,
            "description":        v.description,
            "video_type":         v.video_type,
            "thumbnail_url":      v.thumbnail_url,
            "upload_date":        v.upload_date,
            "top_comments": [
                {
                    "author": c.author,
                    "text":   c.text,
                    "likes":  c.likes,
                    "date":   c.date,
                }
                for c in (v.comments or [])
            ],
        }
