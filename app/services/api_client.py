import asyncio
import zipfile
import io
import time
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import aiohttp
import aiofiles

from ..config import settings

logger = logging.getLogger(__name__)

class APIClient:
    """Клиент для взаимодействия с внешним API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.retry_delay = 1 
        self.max_retries = 10
    
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        candidate_id: Optional[str] = None,
        data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Any:
        """Выполнить запрос с обработкой ошибок и ограничений"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if candidate_id:
            headers["X-Candidate-Id"] = candidate_id
        
        try:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    if endpoint == "/api/files/download":
                        return await response.read()
                    return await response.json()
                
                elif response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited. Retry after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(
                        method, endpoint, candidate_id, data, retry_count + 1
                    )
                
                elif response.status == 403:
                    # Блокировка
                    retry_after = int(response.headers.get("Retry-After", 1800))
                    logger.warning(f"Blocked for {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(
                        method, endpoint, candidate_id, data, retry_count + 1
                    )
                
                elif response.status == 404:
                    error = await response.json()
                    raise Exception(f"Not found: {error.get('detail', 'Unknown error')}")
                
                else:
                    error = await response.json()
                    raise Exception(f"API error {response.status}: {error.get('detail', 'Unknown error')}")
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout on request to {endpoint}, retrying...")
            await asyncio.sleep(self.retry_delay)
            return await self._make_request(
                method, endpoint, candidate_id, data, retry_count + 1
            )
        
        except Exception as e:
            if retry_count < self.max_retries:
                logger.warning(f"Error: {e}, retrying...")
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self._make_request(
                    method, endpoint, candidate_id, data, retry_count + 1
                )
            raise
    
    async def get_names(self, candidate_id: Optional[str] = None) -> List[str]:
        """Получить имена файлов для скачивания"""
        result = await self._make_request(
            "GET", "/api/files/names", candidate_id
        )
        return result.get("file_names", [])
    
    async def download_files(
        self,
        file_names: List[str],
        candidate_id: Optional[str] = None
    ) -> bytes:
        """Скачать файлы по именам"""
        data = {"file_names": file_names}
        return await self._make_request(
            "POST", "/api/files/download", candidate_id, data
        )
    
    async def mark_downloaded(
        self,
        file_names: List[str],
        candidate_id: Optional[str] = None
    ) -> Dict:
        """Отметить файлы как скачанные"""
        data = {"file_names": file_names}
        return await self._make_request(
            "POST", "/api/files/downloaded", candidate_id, data
        )
    
    async def download_all_files(
        self,
        candidate_id: str,
        file_service: 'FileService'
    ) -> Dict[str, Any]:
        """Скачать все файлы"""
        total_downloaded = 0
        total_names = 0
        files_downloaded = []
        start_time = time.time()
        
        while True:
            names = await self.get_names(candidate_id)
            
            if not names:
                break
            
            total_names += len(names)
            
            for i in range(0, len(names), 3):
                batch = names[i:i+3]
                try:
                    zip_data = await self.download_files(batch, candidate_id)

                    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                        for file_info in zf.filelist:
                            content = zf.read(file_info.filename).decode('utf-8')
                            file_service.save_file(
                                candidate_id,
                                file_info.filename,
                                content
                            )
                            files_downloaded.append(file_info.filename)
                            total_downloaded += 1

                    await self.mark_downloaded(batch, candidate_id)
                    
                except Exception as e:
                    logger.error(f"Error downloading batch {batch}: {e}")
            
            await asyncio.sleep(0.5)
        
        elapsed_time = time.time() - start_time
        
        return {
            "total_files": total_downloaded,
            "total_names_fetched": total_names,
            "elapsed_time": elapsed_time,
            "files": files_downloaded
        }