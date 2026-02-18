from fastapi import FastAPI, WebSocket
from database import Base, engine
from routers import users, wallet, games, admin
from websocket_manager import manager

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Commercial Bingo Platform")

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
app.include_router(games.router, prefix="/games", tags=["Games"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

@app.get("/")
def root():
    return {"message": "Bingo Commercial API Running"}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int):
    await manager.connect(room_id, websocket)
    while True:
        data = await websocket.receive_text()
        await manager.broadcast(room_id, {"message": data})
