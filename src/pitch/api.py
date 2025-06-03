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

# Add CORS middleware with specific origins
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
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
    files: list[UploadFile] = File(...)
):
    """Handle file uploads and start analysis"""
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded files and collect paths
        file_paths = []
        try:
            for file in files:
                file_path = await save_upload_file(file)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Failed to save file {file.filename}")
                file_paths.append(file_path)
        except Exception as upload_error:
            return JSONResponse({
                "status": "error",
                "message": f"Error uploading files: {str(upload_error)}"
            }, status_code=400)

        # Validate files
        if not file_paths:
            return JSONResponse({
                "status": "error",
                "message": "No files were uploaded"
            }, status_code=400)

        # Start analysis in background
        background_tasks.add_task(
            analyze_pitch_deck,
            job_id=job_id,
            file_paths=file_paths,
            startup_name=startup_name
        )
        
        # Return success response with WebSocket connection details
        return JSONResponse({
            "status": "started",
            "job_id": job_id,
            "message": "Analysis started successfully",
            "websocket_url": f"/ws/{job_id}"
        })
    except Exception as e:
        # Log the error and return error response
        print(f"Error in /analyze endpoint: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
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

async def analyze_pitch_deck(job_id: str, file_paths: list[str], startup_name: str):
    """Background task to analyze the pitch deck and additional files"""
    try:
        # Initialize status
        await status_manager.broadcast_status(job_id, {
            "status": "started",
            "type": "task_started",
            "message": f"Starting analysis of {len(file_paths)} document(s)",
            "timestamp": datetime.now().isoformat()
        })

        # Validate and organize files
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                invalid_files.append(f"File not found: {os.path.basename(file_path)}")
                continue
                
            ext = os.path.splitext(file_path.lower())[1]
            if ext not in ['.pdf', '.ppt', '.pptx']:
                invalid_files.append(f"Unsupported format for {os.path.basename(file_path)}")
                continue
                
            valid_files.append(file_path)

        if not valid_files:
            raise ValueError("No valid files to analyze.\n" + "\n".join(invalid_files))

        if invalid_files:
            await status_manager.broadcast_status(job_id, {
                "status": "warning",
                "type": "validation_warning",
                "message": "Some files were skipped:\n" + "\n".join(invalid_files),
                "timestamp": datetime.now().isoformat()
            })

        # Initialize crew
        pitch_crew = Pitch()
        
        print(f"\nStarting analysis with:")
        print(f"- Valid files ({len(valid_files)}):")
        for file in valid_files:
            print(f"  - {os.path.basename(file)}")
        print(f"- Startup name: {startup_name}")
        
        # Prepare inputs for the crew
        inputs = {
            'file_paths': ", ".join(valid_files),  # Convert list to comma-separated string for template
            'startup_name': startup_name,
            'current_year': str(datetime.now().year),
            'job_id': job_id,
            'total_files': len(valid_files)
        }

        try:
            # Run crew analysis
            result = pitch_crew.crew().kickoff(inputs=inputs)
            
            # Handle result
            result_text = str(result) if result else "Analysis completed but no results were generated."
            
            # Send completion status
            await status_manager.broadcast_status(job_id, {
                "status": "completed",
                "type": "completed",
                "message": "Analysis completed successfully",
                "result": result_text,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as crew_error:
            error_message = f"Error during crew analysis: {str(crew_error)}"
            print(f"Crew error: {error_message}")
            await status_manager.broadcast_status(job_id, {
                "status": "error",
                "type": "error",
                "message": error_message,
                "timestamp": datetime.now().isoformat()
            })
            raise crew_error

    except Exception as e:
        error_message = f"Error in pitch deck analysis: {str(e)}"
        print(f"Analysis error: {error_message}")
        await status_manager.broadcast_status(job_id, {
            "status": "error",
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        raise e

    finally:
        # Clean up uploaded files
        try:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as cleanup_error:
            print(f"Error cleaning up file(s): {cleanup_error}")

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
