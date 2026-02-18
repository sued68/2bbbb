from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(room_id, []).append(websocket)

    async def broadcast(self, room_id: int, message: dict):
        for connection in self.connections.get(room_id, []):
            await connection.send_json(message)

manager = ConnectionManager()
