import asyncio
import websockets
import json

async def monitor_analysis(job_id):
    async with websockets.connect(f'ws://localhost:8000/ws/{job_id}') as websocket:
        print(f"Connected to WebSocket for job {job_id}")
        try:
            while True:
                message = await websocket.recv()
                print(json.loads(message))
        except websockets.ConnectionClosed:
            print("Connection closed")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python monitor.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    asyncio.run(monitor_analysis(job_id))
