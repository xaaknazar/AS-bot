import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.data import RvoWsDataSchema


router = APIRouter()
websocket_list: list[WebSocket] = []


@router.websocket("/rvo")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_list.append(websocket)
    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        websocket_list.remove(websocket)


async def broadcast_data(data: RvoWsDataSchema) -> None:
    disconnected_clients = []
    message = data.model_dump()

    for websocket in websocket_list:
        try:
            await websocket.send_json(message)
        except Exception:
            disconnected_clients.append(websocket)

    for websocket in disconnected_clients:
        websocket_list.remove(websocket)


def send_rvo_data(
        shift_start: datetime,
        shift_name: str,
        speed: float,
        speed_for_shift: float,
        produced: float
)-> None:
    shift_id = 1 if shift_start.hour == 8 else 2

    data = RvoWsDataSchema(
        shift_id=shift_id,
        shift_name=shift_name,
        speed=speed,
        speed_for_shift=speed_for_shift,
        produced=produced
    )

    asyncio.run(broadcast_data(data))
