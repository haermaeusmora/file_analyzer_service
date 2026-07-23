import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pytz
import aiofiles

class FileService:
    """Сервис для хранения и анализа файлов"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tz = pytz.timezone("Asia/Novosibirsk")
    
    def _get_candidate_dir(self, candidate_id: str) -> Path:
        """Получить директорию кандидата"""
        candidate_dir = self.data_dir / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        return candidate_dir
    
    def _get_metadata_path(self, candidate_id: str) -> Path:
        """Получить путь к файлу метаданных"""
        return self._get_candidate_dir(candidate_id) / "metadata.json"
    
    def _load_metadata(self, candidate_id: str) -> Dict:
        """Загрузить метаданные"""
        metadata_path = self._get_metadata_path(candidate_id)
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return {"files": []}
    
    def _save_metadata(self, candidate_id: str, metadata: Dict):
        """Сохранить метаданные"""
        metadata_path = self._get_metadata_path(candidate_id)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def save_file(self, candidate_id: str, file_name: str, content: str):
        """Сохранить файл и обновить метаданные"""
        candidate_dir = self._get_candidate_dir(candidate_id)
        file_path = candidate_dir / file_name

        with open(file_path, 'w') as f:
            f.write(content)

        metadata = self._load_metadata(candidate_id)

        for f in metadata["files"]:
            if f["name"] == file_name:
                return

        now = datetime.now(self.tz)
        metadata["files"].append({
            "name": file_name,
            "downloaded_at": now.isoformat(),
            "size": len(content)
        })
        
        self._save_metadata(candidate_id, metadata)
    
    def get_downloaded_files(self, candidate_id: str) -> List[Dict]:
        """Получить список скачанных файлов"""
        metadata = self._load_metadata(candidate_id)
        return metadata["files"]
    
    def get_file_content(self, candidate_id: str, file_name: str) -> Optional[str]:
        """Получить содержимое файла"""
        candidate_dir = self._get_candidate_dir(candidate_id)
        file_path = candidate_dir / file_name
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r') as f:
            return f.read()
    
    def analyze_files(
        self,
        file_names: List[str],
        candidate_id: str
    ) -> Dict[str, Any]:
        """Проанализировать выбранные файлы"""
        total_stats = [0] * 10 
        file_stats = {}
        
        for file_name in file_names:
            content = self.get_file_content(candidate_id, file_name)
            if content is None:
                continue
            
            stats = [0] * 10
            for char in content.strip():
                if char.isdigit():
                    digit = int(char)
                    stats[digit] += 1
                    total_stats[digit] += 1
            
            file_stats[file_name] = stats
        
        return {
            "total_stats": total_stats,
            "file_stats": file_stats
        }
    
    def delete_file(self, candidate_id: str, file_name: str):
        """Удалить файл"""
        candidate_dir = self._get_candidate_dir(candidate_id)
        file_path = candidate_dir / file_name
        
        if file_path.exists():
            file_path.unlink()
            
            metadata = self._load_metadata(candidate_id)
            metadata["files"] = [f for f in metadata["files"] if f["name"] != file_name]
            self._save_metadata(candidate_id, metadata)