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

from .crew import Pitch
from .status_manager import status_manager

app = FastAPI(title="Pitch Deck Analyzer")

# Mount static files
app.mount("/static", StaticFiles(directory="src/pitch/static"), name="static")

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
            "message": "Starting pitch deck analysis"
        })

        # Verify the file exists
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
            
        # Run the crew with the inputs
        inputs = {
            'file_path': file_path,
            'startup_name': startup_name,
            'current_year': '2025',  # Add current year as required by main.py
            'job_id': job_id  # Pass job_id to allow tasks to update status
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
            
            # Send completion status
            await status_manager.broadcast_status(job_id, {
                "status": "completed",
                "type": "completed",
                "message": "Analysis completed successfully",
                "result": result
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

@app.get("/")
async def read_root():
    """Serve the index.html file"""
    return FileResponse("src/pitch/static/index.html")

# Server will be started by uvicorn
