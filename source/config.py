from typing import Optional, Dict, Any
import json
import os

class AppConfig:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _DEFAULT_PATH = os.path.join(_BASE_DIR, "config.json")

    def __init__(self) -> None:
        self.start_url: str = "https://example.com"
        self.max_depth: int = 10
        self.max_links_per_page: int = 10
        self.thread_count: int = 5
        self.output_dir: str = "./archive"
        self.proxy_url: Optional[str] = None

    def load_from_file(self, filepath: Optional[str] = None) -> bool:
        target_path = filepath or self._DEFAULT_PATH
        
        if not os.path.exists(target_path):
            self.save_to_file(target_path)
            return True

        try:
            with open(target_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                self.start_url = data.get("start_url", self.start_url)
                self.max_depth = data.get("max_depth", self.max_depth)
                self.max_links_per_page = data.get("max_links_per_page", self.max_links_per_page)
                self.thread_count = data.get("thread_count", self.thread_count)
                self.output_dir = data.get("output_dir", self.output_dir)
                self.proxy_url = data.get("proxy_url", self.proxy_url)
            return True
        except Exception as e:
            print(f"[Config Error] Failed to load from {target_path}: {e}")
            return False

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        target_path = filepath or self._DEFAULT_PATH
        try:
            with open(target_path, "w", encoding="utf-8") as file:
                json.dump({
                    "start_url": self.start_url,
                    "max_depth": self.max_depth,
                    "max_links_per_page": self.max_links_per_page,
                    "thread_count": self.thread_count,
                    "output_dir": self.output_dir,
                    "proxy_url": self.proxy_url
                }, file, indent=4)
            return True
        except Exception as e:
            print(f"[Config Error] Failed to save to {target_path}: {e}")
            return False

    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        for key, value in new_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)

config = AppConfig()
config.load_from_file()
