from typing import Optional, List, Any, Dict
from pydantic import BaseModel


class ScanStartRequest(BaseModel):
    local_ip: str


class ScanStatusResponse(BaseModel):
    is_scanning: bool
    progress: int
    current_ip: str
    results: List[Dict[str, Any]]
    error: Optional[str] = None
