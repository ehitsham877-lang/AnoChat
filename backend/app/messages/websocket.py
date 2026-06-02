from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.messages.sanitize import sanitize_chatter_message

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, chatter_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms[chatter_id].append(websocket)

    def disconnect(self, chatter_id: int, websocket: WebSocket) -> None:
        if websocket in self.rooms[chatter_id]:
            self.rooms[chatter_id].remove(websocket)

    async def broadcast(self, chatter_id: int, payload: dict) -> None:
        for socket in list(self.rooms[chatter_id]):
            await socket.send_json(payload)


manager = ConnectionManager()


@router.websocket("/ws/chatters/{chatter_id}")
async def chatter_socket(websocket: WebSocket, chatter_id: int):
    await manager.connect(chatter_id, websocket)
    await manager.broadcast(chatter_id, {"type": "presence", "status": "online"})
    try:
        while True:
            payload = await websocket.receive_json()
            if isinstance(payload, dict):
                for key in ("body", "message", "text", "content"):
                    if key in payload and isinstance(payload[key], str):
                        payload[key] = sanitize_chatter_message(payload[key])
            await manager.broadcast(chatter_id, payload)
    except WebSocketDisconnect:
        manager.disconnect(chatter_id, websocket)
        await manager.broadcast(chatter_id, {"type": "presence", "status": "offline"})
