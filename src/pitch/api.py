from fastapi import FastAPI, File, UploadFile, WebSocket, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import uuid
import os
from typing import Dict
import aiofiles
import asyncio

from .crew import Pitch
from .status_manager import status_manager

app = FastAPI(title="Pitch Deck Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file and return the path"""
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{upload_file.filename}")
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
            "message": "Starting pitch deck analysis"
        })

        # Run the crew with the inputs
        inputs = {
            'file_path': file_path,
            'startup_name': startup_name
        }

        # Run tasks and send updates
        result = pitch_crew.crew().kickoff(inputs=inputs)

        # Send completion status
        await status_manager.broadcast_status(job_id, {
            "status": "completed",
            "message": "Analysis completed",
            "result": result
        })

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

@app.post("/analyze")
async def create_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    startup_name: str = Form(default="Unknown Startup")
):
    """
    Upload a pitch deck (PDF/PPT) and start the analysis
    """
    if not file.filename.lower().endswith(('.pdf', '.ppt', '.pptx')):
        return JSONResponse(
            status_code=400,
            content={"error": "Only PDF and PPT/PPTX files are supported"}
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save the uploaded file
    file_path = await save_upload_file(file)

    # Start analysis in background
    background_tasks.add_task(
        analyze_pitch_deck,
        job_id=job_id,
        file_path=file_path,
        startup_name=startup_name or "unknown"
    )

    return {
        "job_id": job_id,
        "message": "Analysis started",
        "websocket_url": f"/ws/{job_id}"
    }

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time status updates"""
    await status_manager.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()
    except:
        status_manager.disconnect(websocket, job_id)

# Server will be started by uvicorn
