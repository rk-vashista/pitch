from typing import Dict, Set
import json
from fastapi import WebSocket

class StatusManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)

    def disconnect(self, websocket: WebSocket, job_id: str):
        self.active_connections[job_id].remove(websocket)
        if not self.active_connections[job_id]:
            del self.active_connections[job_id]

    async def broadcast_status(self, job_id: str, status: dict):
        if job_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_text(json.dumps(status))
                except:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_connection in dead_connections:
                self.active_connections[job_id].remove(dead_connection)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

status_manager = StatusManager()
