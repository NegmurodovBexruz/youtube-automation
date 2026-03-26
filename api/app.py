"""
FastAPI app — PostgreSQL init qo'shildi
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.job_manager import JobManager, JobStatus
from api.ws_manager import WebSocketManager
from utils.database import Database, close_db, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

job_manager = JobManager()
ws_manager  = WebSocketManager()
db          = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — DB jadvallarini yaratish
    try:
        await init_db()
        logger.info("PostgreSQL ulandi ✓")
    except Exception as e:
        logger.warning(f"PostgreSQL ulanmadi (ilovasiz ishlaydi): {e}")

    yield

    # Shutdown
    await close_db()
    await job_manager.cleanup()
    logger.info("Server to'xtatildi")


app = FastAPI(
    title="YouTube Automation API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
os.makedirs("static", exist_ok=True)
os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")


# ── Schemalar ────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    query:       str  = "you tube"
    max_videos:  int  = 10
    headless:    bool = True
    parallel:    bool = False
    workers:     int  = 3
    save_format: str  = "both"   # json | csv | both | db | all


class ScrapeResponse(BaseModel):
    job_id:  str
    message: str
    ws_url:  str


# ── Endpoints ────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/scrape", response_model=ScrapeResponse)
async def start_scrape(req: ScrapeRequest):
    job_id = str(uuid.uuid4())[:8]
    logger.info(f"Yangi job: {job_id} | query='{req.query}'")

    # DB ga job yozish (ixtiyoriy)
    try:
        await db.create_job(
            job_id, req.query,
            max_videos=req.max_videos,
            headless=req.headless,
            parallel=req.parallel,
        )
    except Exception as e:
        logger.warning(f"Job DB ga yozilmadi: {e}")

    asyncio.create_task(
        job_manager.run_job(job_id, req, ws_manager, db)
    )

    return ScrapeResponse(
        job_id=job_id,
        message=f"Scraping boshlandi: '{req.query}'",
        ws_url=f"/ws/{job_id}",
    )


@app.get("/api/jobs")
async def list_jobs():
    """Avval DB dan, bo'lmasa memory dan"""
    try:
        return await db.list_jobs()
    except Exception:
        return job_manager.list_jobs()


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    # Memory dan (tez)
    job = job_manager.get_job(job_id)
    if job:
        return job
    # DB dan fallback
    try:
        job = await db.get_job(job_id)
        if job:
            return job
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Job topilmadi")


@app.get("/api/jobs/{job_id}/results")
async def get_results(job_id: str):
    # Memory dan
    job = job_manager.get_job(job_id)
    if job:
        if job["status"] != JobStatus.DONE:
            raise HTTPException(status_code=202, detail=f"Hali tugamagan: {job['status']}")
        return {"job_id": job_id, "videos": job.get("videos", []), "source": "memory"}

    # DB dan
    try:
        videos = await db.get_videos(job_id)
        if videos:
            return {"job_id": job_id, "videos": videos, "source": "database"}
    except Exception as e:
        logger.warning(f"DB dan olishda xato: {e}")

    raise HTTPException(status_code=404, detail="Natija topilmadi")


@app.get("/api/jobs/{job_id}/analytics")
async def get_analytics(job_id: str):
    job = job_manager.get_job(job_id)
    if job and job["status"] == JobStatus.DONE:
        return {"job_id": job_id, "analytics": job.get("analytics", {}), "source": "memory"}

    try:
        analytics = await db.get_analytics(job_id)
        if analytics:
            return {"job_id": job_id, "analytics": analytics, "source": "database"}
    except Exception as e:
        logger.warning(f"DB analytics xato: {e}")

    raise HTTPException(status_code=404, detail="Analytics topilmadi")


@app.get("/api/jobs/{job_id}/report")
async def get_report(job_id: str):
    import pathlib
    path = pathlib.Path(f"output/{job_id}/report.html")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Hisobot topilmadi")
    return FileResponse(str(path), media_type="text/html")


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    job_manager.delete_job(job_id)
    try:
        await db.update_job_status(job_id, "deleted")
    except Exception:
        pass
    return {"message": f"Job o'chirildi: {job_id}"}


@app.get("/api/stats")
async def global_stats():
    """PostgreSQL dan umumiy statistika"""
    try:
        return await db.get_global_stats()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB ulanmagan: {e}")


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await ws_manager.connect(job_id, websocket)
    try:
        job = job_manager.get_job(job_id)
        if job and job["status"] == JobStatus.DONE:
            await ws_manager.send(job_id, {
                "type": "done", "job_id": job_id,
                "total": job.get("total_videos", 0),
                "videos": job.get("videos", []),
                "analytics": job.get("analytics", {}),
            })
        elif job and job["status"] == JobStatus.ERROR:
            await ws_manager.send(job_id, {
                "type": "error", "message": job.get("error", "Xato"),
            })

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text('{"type":"ping"}')
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS xato: {e}")
    finally:
        ws_manager.disconnect(job_id, websocket)


@app.get("/health")
async def health():
    db_ok = False
    try:
        stats = await db.get_global_stats()
        db_ok = True
    except Exception:
        stats = {}
    return {
        "status":       "ok",
        "database":     "connected" if db_ok else "disconnected",
        "active_jobs":  job_manager.active_count(),
        "ws_clients":   ws_manager.connection_count(),
        "db_stats":     stats,
    }
