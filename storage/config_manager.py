import json
import os
from typing import List, Optional

class ConfigManager:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(base_dir, "storage", "data")
        self.config_file = os.path.join(self.data_dir, "mru.json")
        self._ensure_dir()

    def _ensure_dir(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
        except Exception:
            pass

    def _load_config(self) -> dict:
        if not os.path.exists(self.config_file):
            return {"last_directory": None, "mru_paths": []}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"last_directory": None, "mru_paths": []}

    def _save_config(self, data: dict):
        self._ensure_dir()
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_last_directory(self) -> Optional[str]:
        cfg = self._load_config()
        last_dir = cfg.get("last_directory")
        if last_dir and os.path.isdir(last_dir):
            return last_dir
        return None

    def set_last_directory(self, path: str):
        if not path:
            return
        directory = os.path.dirname(path) if os.path.isfile(path) else path
        if not os.path.isdir(directory):
            return
        cfg = self._load_config()
        cfg["last_directory"] = directory
        self._save_config(cfg)

    def get_mru_paths(self) -> List[str]:
        cfg = self._load_config()
        mru = cfg.get("mru_paths", [])
        return [p for p in mru if os.path.exists(p)]

    def add_mru_path(self, path: str):
        if not path:
            return
        cfg = self._load_config()
        mru = cfg.get("mru_paths", [])
        # Remove if already exists so it moves to front
        mru = [p for p in mru if p != path]
        mru.insert(0, path)
        # Limit to 10
        cfg["mru_paths"] = mru[:10]
        # Also update last directory
        directory = os.path.dirname(path) if os.path.isfile(path) else path
        if os.path.isdir(directory):
            cfg["last_directory"] = directory
        self._save_config(cfg)

config_manager = ConfigManager()
