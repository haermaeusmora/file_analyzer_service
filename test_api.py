from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
import uuid
import random
import zipfile
import io

app = FastAPI(title="Test File API")

FILES = {}
for _ in range(50):
    file_id = uuid.uuid4()
    content = ''.join(str(random.randint(0, 9)) for _ in range(500))
    FILES[f"{file_id}.txt"] = content

downloaded = {}

class DownloadRequest(BaseModel):
    file_names: List[str]

class MarkDownloadedRequest(BaseModel):
    file_names: List[str]

@app.get("/api/files/names")
async def get_names(x_candidate_id: Optional[str] = Header(None)):
    client_id = x_candidate_id or "default"
    
    already = downloaded.get(client_id, set())
    available = [f for f in FILES.keys() if f not in already]
    
    if not available:
        return {"file_names": []}
    
    count = min(random.randint(3, 9), len(available))
    chosen = random.sample(available, count)
    
    return {"file_names": chosen}

@app.post("/api/files/download")
async def download_files(request: DownloadRequest, x_candidate_id: Optional[str] = Header(None)):
    if len(request.file_names) > 3:
        raise HTTPException(status_code=400, detail="Too many files. Max 3 per request.")

    missing = [f for f in request.file_names if f not in FILES]
    if missing:
        raise HTTPException(status_code=404, detail=f"Files not found: {missing}")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for name in request.file_names:
            content = FILES[name]
            zf.writestr(name, content)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip"
    )

@app.post("/api/files/downloaded")
async def mark_downloaded(request: MarkDownloadedRequest, x_candidate_id: Optional[str] = Header(None)):
    client_id = x_candidate_id or "default"
    
    if client_id not in downloaded:
        downloaded[client_id] = set()
    
    marked_now = 0
    already_marked = 0
    
    for name in request.file_names:
        if name in FILES:
            if name in downloaded[client_id]:
                already_marked += 1
            else:
                downloaded[client_id].add(name)
                marked_now += 1
    
    return {"marked_now": marked_now, "already_marked": already_marked}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)