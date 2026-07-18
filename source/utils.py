import os
from typing import Optional

from source.page import WebPage


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

def web_page_showcase(page: WebPage) -> str:
    path = page.url.path.split("/")[-1]
    title = page.page_title
    if path.lower() in title.lower():
        return shortner(page.page_title, head=15, tail=13)
    elif title.lower() in path.lower():
        return shortner(path, head=15, tail=10)
    else:
        return shortner(page.page_title, head=15, tail=13) + " -- " + shortner(path, head=15, tail=10)
