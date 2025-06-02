from typing import Dict, Set
import json
from fastapi import WebSocket

class StatusManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.job_logs: Dict[str, list] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        
        # Send previous logs if they exist
        if job_id in self.job_logs:
            for log in self.job_logs[job_id]:
                await websocket.send_text(json.dumps(log))

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    def _serialize_value(self, value):
        """Helper method to make values JSON serializable"""
        if hasattr(value, '__dict__'):
            return str(value)
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        return value

    async def broadcast_status(self, job_id: str, status: dict):
        # Store the log
        if job_id not in self.job_logs:
            self.job_logs[job_id] = []
            
        # Make status JSON serializable
        serializable_status = self._serialize_value(status)
        self.job_logs[job_id].append(serializable_status)

        if job_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_text(json.dumps(serializable_status))
                except Exception as e:
                    print(f"Error sending message: {str(e)}")
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_connection in dead_connections:
                self.active_connections[job_id].remove(dead_connection)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    def clear_job_logs(self, job_id: str):
        if job_id in self.job_logs:
            del self.job_logs[job_id]

status_manager = StatusManager()
