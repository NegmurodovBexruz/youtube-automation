"""
WebSocket ulanishlarini boshqarish — bir job uchun bir nechta client bo'lishi mumkin
"""

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Har bir job_id uchun bir yoki bir nechta WebSocket ulanishni boshqaradi.
    Thread-safe broadcast.
    """

    def __init__(self):
        # job_id -> [WebSocket, ...]
        self._connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._connections[job_id].append(websocket)
        # Darhol "connected" xabari yuborish
        await self.send(job_id, {"type": "connected", "job_id": job_id})

    def disconnect(self, job_id: str, websocket: WebSocket):
        conns = self._connections.get(job_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns and job_id in self._connections:
            del self._connections[job_id]

    async def send(self, job_id: str, data: Any):
        """Bitta job ning barcha ulanishlariga xabar yuborish"""
        payload = json.dumps(data, ensure_ascii=False, default=str)
        dead = []
        for ws in list(self._connections.get(job_id, [])):
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.debug(f"WS send xato (job={job_id}): {e}")
                dead.append(ws)
        # O'lik ulanishlarni tozalash
        for ws in dead:
            self.disconnect(job_id, ws)

    async def broadcast(self, data: Any):
        """Barcha ulanishlarga yuborish"""
        for job_id in list(self._connections.keys()):
            await self.send(job_id, data)

    def connection_count(self) -> int:
        return sum(len(v) for v in self._connections.values())
