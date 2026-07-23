import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import pytz

from .config import settings
from .services.api_client import APIClient
from .services.file_service import FileService
from .models import FileStats, AllStatsResponse, FileStatsResponse

app = FastAPI(title="File Analyzer Service")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

api_client = APIClient(base_url=settings.API_BASE_URL)
file_service = FileService(data_dir=settings.DATA_DIR)

stats_store = {}

START_TIME = datetime.now(pytz.timezone("Asia/Novosibirsk"))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{ start_time }}", START_TIME.strftime("%Y-%m-%d %H:%M:%S"))
    return HTMLResponse(html)

@app.get("/api/files")
async def get_files(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    candidate_id: Optional[str] = None
):
    """Получить список скачанных файлов с пагинацией"""
    if not candidate_id:
        candidate_id = str(uuid.uuid4())
    
    all_files = file_service.get_downloaded_files(candidate_id)
    total = len(all_files)

    all_files.sort(key=lambda x: x['downloaded_at'], reverse=True)

    start = (page - 1) * per_page
    end = start + per_page
    files = all_files[start:end]
    
    return {
        "files": files,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
    }

@app.post("/api/files/download")
async def download_files(candidate_id: Optional[str] = None):
    """Запустить процесс скачивания файлов"""
    if not candidate_id:
        candidate_id = str(uuid.uuid4())
    
    try:
        result = await api_client.download_all_files(candidate_id, file_service)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/analyze")
async def analyze_files(
    file_names: List[str],
    candidate_id: Optional[str] = None
):
    """Проанализировать выбранные файлы"""
    if not candidate_id:
        candidate_id = str(uuid.uuid4())
    
    try:
        stats = file_service.analyze_files(file_names, candidate_id)

        stats_id = str(uuid.uuid4())
        stats_store[stats_id] = stats
        
        return {
            "stats_id": stats_id,
            "total_stats": stats['total_stats'],
            "file_stats": stats['file_stats']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/stats/{stats_id}")
async def get_stats(stats_id: str):
    """Получить сохраненную статистику"""
    if stats_id not in stats_store:
        raise HTTPException(status_code=404, detail="Stats not found")
    return stats_store[stats_id]

@app.get("/api/status")
async def get_status(candidate_id: Optional[str] = None):
    """Получить статус скачивания"""
    if not candidate_id:
        candidate_id = str(uuid.uuid4())
    
    downloaded = file_service.get_downloaded_files(candidate_id)
    return {
        "downloaded_count": len(downloaded),
        "candidate_id": candidate_id
    }