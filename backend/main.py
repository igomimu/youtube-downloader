import os
import asyncio
import json
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Data models
class VideoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_id: str = "best"

# Helper for yt-dlp progress
def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            p = d.get('_percent_str', '0%').replace('%','')
            progress_data = {
                "status": "downloading",
                "filename": d.get('filename'),
                "percentage": p,
                "speed": d.get('_speed_str'),
                "eta": d.get('_eta_str')
            }
            # Since this hook runs in a thread, we need to schedule the async broadcast
            # But checking if loop is running is tricky. 
            # For simplicity in this synchronous hook, we might skip direct async calls 
            # or use a thread-safe way. 
            # However, for a simple local app, we can try to run it.
            # A common pattern is writing to a queue or just printing.
            # For this MVP, let's try to just print to console, 
            # and maybe figure out a better way to push to WS if needed.
            # actually, let's use a workaround to send message to the event loop
            pass 
        except Exception as e:
            print(f"Error in hook: {e}")

    elif d['status'] == 'finished':
        print('Download complete')

# Better approach for Thread-safe WS broadcast:
# We will use a shared queue or similar if we strictly need real-time WS updates from the hook.
# But for now, let's just implement the endpoints and the basic logic.
# I will implement a simplified progress sending mechanism later or use polling if WS is too complex for V1.
# Actually, let's just use a global variable for status and let the frontend poll or have the WS loop watch it?
# No, let's do it properly with an async wrapper if possible, or just standard synchronous download for now 
# and maybe skip detailed progress bar for the VERY first step if it complicates things.
# BUT the user wanted a "modern" app. Progress bars are essential.
# I'll try to use a class that holds state and an asyncio task that watches it.

class DownloadManager:
    def __init__(self):
        self.current_status = {}

    def hook(self, d):
        if d['status'] == 'downloading':
            self.current_status = {
                "status": "downloading",
                "percent": d.get('_percent_str', '').strip(),
                "speed": d.get('_speed_str', '').strip(),
                "eta": d.get('_eta_str', '').strip(),
                "filename": os.path.basename(d.get('filename', ''))
            }
            print(f"Progress: {self.current_status}") # Debug
        elif d['status'] == 'finished':
            self.current_status = {"status": "finished", "filename": d.get('filename')}

download_manager = DownloadManager()

async def broadcast_progress():
    last_status = {}
    while True:
        if download_manager.current_status != last_status:
            await manager.broadcast(json.dumps(download_manager.current_status))
            last_status = download_manager.current_status.copy()
        if last_status.get('status') == 'finished':
             # Keep broadcasting finished for a moment or just reset?
             # Let's just wait a bit and then clear?
             # actually if we break, we stop sending updates.
             pass
        await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_progress())

@app.post("/info")
def get_info(req: VideoRequest):
    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True, # Ensure we process single video even if URL has &list
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            # Filter and simplify formats for frontend
            formats = []
            
            # If it's still a playlist for some reason (e.g. strict playlist URL), try to get first entry
            if info.get('_type') == 'playlist':
                 if info.get('entries') and len(info['entries']) > 0:
                     info = info['entries'][0]
            
            for f in info.get('formats', []):
                # Relaxed filter: Allow mp4 and webm, ensure it's a video
                if f.get('vcodec') != 'none': 
                    formats.append({
                        'format_id': f['format_id'],
                        'resolution': f.get('resolution') or 'audio only',
                        'ext': f['ext'],
                        'filesize': f.get('filesize'),
                        'note': f.get('format_note')
                    })
            
            # Sort formats by resolution (descending) to show best first
            # Simple heuristic: resolution string comparison isn't perfect but works for common cases like '1080p' > '720p'
            # Better: use height if available
            formats.sort(key=lambda x: x.get('filesize') or 0, reverse=True)

            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "formats": formats
            }
    except Exception as e:
        print(f"Error extracting info: {e}")
        raise HTTPException(status_code=400, detail=str(e))

def run_download(url: str, format_id: str):
    # Save to Windows Desktop for easier access
    # WSL path for C:\Users\lucky\Desktop\TubeDownloads
    save_path = "/mnt/c/Users/lucky/Desktop/TubeDownloads"
    os.makedirs(save_path, exist_ok=True)
    
    ydl_opts = {
        'format': f"{format_id}+bestaudio/best",
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'progress_hooks': [download_manager.hook],
        # 'merge_output_format': 'mp4', # Optional: ensure final container is mp4 if desired
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

@app.post("/download")
async def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    # Reset status
    download_manager.current_status = {"status": "starting"}
    background_tasks.add_task(run_download, req.url, req.format_id)
    return {"message": "Download started"}

@app.get("/")
def read_root():
    return {"message": "YouTube Downloader Backend is running. Please use the Frontend at http://localhost:5173"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection open
    except WebSocketDisconnect:
        manager.disconnect(websocket)
