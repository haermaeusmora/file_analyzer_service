from pydantic import BaseModel
from typing import List, Optional

class FileStats(BaseModel):
    total_stats: List[int]
    file_stats: dict

class AllStatsResponse(BaseModel):
    stats_id: str
    total_stats: List[int]
    file_stats: dict

class FileStatsResponse(BaseModel):
    files: List[dict]
    total: int
    page: int
    per_page: int
    total_pages: int