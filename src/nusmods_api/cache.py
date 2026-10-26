"""Local cache for NUSMods API data."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

class Cache:
    def __init__(
        self,
        directory: str | Path = ".nusmods_cache",
        expiration: int | None = 86_400,
    ) -> None:
        self.directory = Path(directory)
        self.expiration = expiration
        self.directory.mkdir(parents=True, exist_ok=True)
        
    def _path_for(self, key: str) -> Path:
        filename = hashlib.sha256(
            key.encode()
        ).hexdigest() + ".json"
        
        return self.directory / filename
    
    def get(self, key: str) -> Any | None:
        path = self._path_for(key)
        if not path.exists():
            return None
        
        if self.expiration is not None and time.time() - path.stat().st_mtime > self.expiration:
            path.unlink()
            return None
        
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        
    def set(self, key: str, value: Any) -> None:
        path = self._path_for(key)
        temp_path = path.with_suffix(".tmp")
        
        temp_path.write_text(
            json.dumps(value, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(path)
        
    def delete(self, key: str) -> None:
        path = self._path_for(key)
    
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        
    def clear(self) -> None:
        for file in self.directory.glob("*.json"):
            try:
                file.unlink()
            except FileNotFoundError:
                pass