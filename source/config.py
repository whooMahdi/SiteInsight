from typing import Optional, Dict, Any
import json
import os
import tools

class AppConfig:
 
    def __init__(
            self, 
            start_url: str, 
            max_depth: int = 10, 
            max_links_per_page: int = 10, 
            thread_count: int = 5, 
            output_dir : str = "output", 
            proxy_url: str = ""
        ) -> None:

        self.start_url = start_url
        self.max_depth = max_depth
        self.max_links_per_page = max_links_per_page
        self.thread_count = thread_count
        self.output_dir = output_dir
        self.proxy_url = proxy_url

    DEFAULT_CONFIG_PATH = "config.json"

    def load_from_file(self, filepath: str = DEFAULT_CONFIG_PATH) -> bool:

        try:
            if not os.path.exists(filepath):
                raise Exception("File doesn't exist")
            with open(filepath, "r", encoding="utf-8") as file:
                data = dict(json.load(file))
                if not set(data.keys()).issubset(self.__dict__.keys()):
                    raise Exception("Config file is not valid,\nthere are/is key(s) that are not valid in the config system")
                elif any((not isinstance(data[k], type(self.__dict__[k])) for k in data.keys())):
                    raise Exception("Config file is not valid,\nthere are/is value(s) that their type is not mached with the config system")
                else:
                    self.__dict__.update(data)
            return True
        except Exception as e:
            print(f"Config Error: Failed to load from {tools.get_abs_path(filepath)}: {e}")
        return False

    def save_to_file(self, filepath: str = DEFAULT_CONFIG_PATH) -> bool:
        try:
            with open(filepath, "w", encoding="utf-8") as file:
                json.dump(self.__dict__, file)
            return True
        except Exception as e:
            print(f"Config Error: Failed to save to {tools.get_abs_path(filepath)}: {e}")
        return False

    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        for key, value in new_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __str__(self) -> str:
        return str(self.__dict__)

# config = AppConfig("hello")
# config.load_from_file()
# print(config)
# config.update_settings({"start_url": "github.com"})
# config.save_to_file()
# print(config)