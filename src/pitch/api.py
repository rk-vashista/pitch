from fastapi import FastAPI, File, UploadFile, WebSocket, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import uuid
import os
from typing import Dict
import aiofiles
import asyncio
from datetime import datetime

from .crew import Pitch
from .status_manager import status_manager

app = FastAPI(title="Pitch Deck Analyzer")

# Mount static files first
app.mount("/static", StaticFiles(directory="src/pitch/static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def home():
    """Serve the home page"""
    return FileResponse("src/pitch/static/index.html")

@app.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    startup_name: str = Form(...),
    file: UploadFile = File(...)
):
    """Handle file upload and start analysis"""
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = await save_upload_file(file)
        
        # Start analysis in background
        background_tasks.add_task(
            analyze_pitch_deck,
            job_id=job_id,
            file_path=file_path,
            startup_name=startup_name
        )
        
        return JSONResponse({
            "status": "started",
            "job_id": job_id,
            "websocket_url": f"/ws/{job_id}"
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file and return the path"""
    # Get absolute path
    abs_upload_dir = os.path.abspath(UPLOAD_DIR)
    file_path = os.path.join(abs_upload_dir, f"{uuid.uuid4()}_{upload_file.filename}")
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await upload_file.read()
        await out_file.write(content)
    return file_path

async def analyze_pitch_deck(job_id: str, file_path: str, startup_name: str):
    """Background task to analyze the pitch deck"""
    pitch_crew = Pitch()
    
    try:
        # Initialize
        await status_manager.broadcast_status(job_id, {
            "status": "started",
            "type": "task_started",
            "message": "Starting pitch deck analysis",
            "timestamp": datetime.now().isoformat()
        })

        # Verify the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Upload file not found at {file_path}")
            
        # Run the crew with the inputs
        inputs = {
            'file_path': file_path,
            'startup_name': startup_name,
            'current_year': '2025',
            'job_id': job_id
        }
        
        print(f"\nStarting analysis with:")
        print(f"- File path: {file_path}")
        print(f"- Startup name: {startup_name}")
        print(f"- File exists: {os.path.exists(file_path)}")
        print(f"- File type:", "PDF" if file_path.lower().endswith('.pdf') else "PPT" if file_path.lower().endswith(('.ppt', '.pptx')) else "Unknown")
        print(f"- Directory contents of {os.path.dirname(file_path)}:")
        print('\n'.join(f"  - {f}" for f in os.listdir(os.path.dirname(file_path))))

        # Run tasks and send updates
        try:
            result = pitch_crew.crew().kickoff(inputs=inputs)
            
            # Convert CrewOutput to string if needed
            result_text = str(result) if result else ""
            
            # Send completion status
            await status_manager.broadcast_status(job_id, {
                "status": "completed",
                "type": "completed",
                "message": "Analysis completed successfully",
                "result": result_text
            })
        except Exception as crew_error:
            await status_manager.broadcast_status(job_id, {
                "status": "error",
                "type": "error",
                "message": f"Error during analysis: {str(crew_error)}"
            })
            raise crew_error

    except Exception as e:
        await status_manager.broadcast_status(job_id, {
            "status": "error",
            "message": f"Error during analysis: {str(e)}"
        })
    finally:
        # Cleanup uploaded file
        try:
            os.remove(file_path)
        except:
            pass

# Previous duplicate route handlers removed

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    await status_manager.connect(job_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        status_manager.disconnect(websocket, job_id)

# Server will be started by uvicorn
