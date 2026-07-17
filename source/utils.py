import os
from typing import Optional


def get_abs_path(path: str):
    try:
        return os.path.abspath(path)
    except:
        return "(No file exists to find abs path)"
    

def shortner(
        value,
        head: int = 25,
        tail: int = 15,
        threshold: Optional[int] = None
    ) -> str:
    threshold = threshold or (head + tail)
    text = str(value) if not isinstance(value, str) else value
    text = " ".join(text.split())

    return (
        f"{text[:head]}...{text[-tail:] if tail else ''}"
        if len(text) > threshold else
        text
    )