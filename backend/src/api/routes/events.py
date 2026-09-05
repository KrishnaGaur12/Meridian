"""
Real-Time Event Stream & Broadcaster (Server-Sent Events).
Provides real-time event distribution for dispute creation, analysis lifecycle,
evidence mutations, and dashboard updates.
"""

import asyncio
import json
from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/events", tags=["Real-Time Events"])


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventBroadcaster:
    """In-memory Pub/Sub broadcaster for Server-Sent Events (SSE)."""

    def __init__(self, max_history: int = 100):
        self.subscribers: Set[asyncio.Queue] = set()
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self.subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue):
        async with self._lock:
            self.subscribers.discard(q)

    def broadcast_sync(self, event_type: str, dispute_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Synchronous wrapper to broadcast an event across all active subscriber queues."""
        evt = {
            "event_type": event_type,
            "dispute_id": dispute_id,
            "timestamp": utc_now_iso(),
            "data": data or {}
        }
        self.history.append(evt)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Broadcast to all live subscriber queues
        dead_queues = []
        for q in list(self.subscribers):
            try:
                q.put_nowait(evt)
            except Exception:
                dead_queues.append(q)
        for dead in dead_queues:
            self.subscribers.discard(dead)

    async def broadcast(self, event_type: str, dispute_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Async broadcast method."""
        self.broadcast_sync(event_type, dispute_id, data)

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self.history[-limit:]))


# Global broadcaster singleton
broadcaster = EventBroadcaster()


def publish_realtime_event(event_type: str, dispute_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
    """Global helper function to broadcast a system event."""
    broadcaster.broadcast_sync(event_type=event_type, dispute_id=dispute_id, data=data)


@router.get("", status_code=status.HTTP_200_OK)
async def event_stream_endpoint(request: Request):
    """
    Server-Sent Events (SSE) stream endpoint.
    Clients connect here to receive real-time updates for:
    - DISPUTE_CREATED
    - DISPUTE_ANALYSIS_STARTED
    - ML_ANALYSIS_COMPLETED
    - DEEPSEEK_ANALYSIS_COMPLETED
    - DISPUTE_ANALYSIS_COMPLETED
    - EVIDENCE_APPROVED
    - DISPUTE_STAGE_CHANGED
    - DASHBOARD_UPDATED
    """
    queue = await broadcaster.subscribe()

    async def event_generator():
        try:
            # Send initial connected message
            initial_payload = json.dumps({"status": "CONNECTED", "timestamp": utc_now_iso()})
            yield f"event: ping\ndata: {initial_payload}\n\n"

            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break

                try:
                    # Wait for next event with a 15-second timeout for keepalive
                    evt = await asyncio.wait_for(queue.get(), timeout=15.0)
                    evt_name = evt.get("event_type", "message")
                    evt_data = json.dumps(evt)
                    yield f"event: {evt_name}\ndata: {evt_data}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping comment
                    yield f": ping {utc_now_iso()}\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            await broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/recent", status_code=status.HTTP_200_OK)
def get_recent_events_endpoint(limit: int = 30):
    """Retrieves list of recently broadcasted real-time events."""
    events = broadcaster.get_recent_events(limit=limit)
    return {
        "total": len(events),
        "events": events
    }
