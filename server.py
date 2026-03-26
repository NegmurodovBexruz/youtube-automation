"""
FastAPI serverni ishga tushirish
"""
import asyncio
import sys
import uvicorn

if __name__ == "__main__":
    # Windows uchun SelectorEventLoop kerak (Playwright talab qiladi)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    uvicorn.run(
        "api.app:app",
        host="localhost",
        port=8000,
        reload=False,
        log_level="info",
    )