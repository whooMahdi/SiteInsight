import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from source.page import WebPage

# Matches the folders Crawler._save_page writes pages into.
CATEGORY_ORDER = ["article", "product", "gallery"]


@dataclass
class PageRef:
    """A lightweight reference to a saved page — enough to list it in a sidebar
    without loading its full content."""
    folder: Path
    title: str
    url: str
    page_type: str


class PageArchive:
    """Scans a Crawler output directory and loads the pages saved in it."""

    def __init__(self, root: str):
        self.root = Path(root)

    def scan(self) -> Dict[str, List[PageRef]]:
        groups: Dict[str, List[PageRef]] = {}

        for category in CATEGORY_ORDER:
            category_dir = self.root / category
            if not category_dir.is_dir():
                continue

            refs: List[PageRef] = []
            for page_dir in sorted(category_dir.iterdir()):
                content_file = page_dir / "content.json"
                if not content_file.is_file():
                    continue
                try:
                    with open(content_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue

                refs.append(PageRef(
                    folder=page_dir,
                    title=data.get("page_title") or page_dir.name,
                    url=data.get("url", ""),
                    page_type=data.get("page_type", category),
                ))

            if refs:
                refs.sort(key=lambda r: r.title.lower())
                groups[category] = refs

        return groups

    def has_reports(self) -> bool:
        return (
            (self.root / "report.txt").is_file()
            or (self.root / "sitemap.txt").is_file()
            or (self.root / "pagerank.txt").is_file()
        )

    @staticmethod
    def load_page(page_ref: PageRef) -> WebPage:
        content_file = page_ref.folder / "content.json"
        with open(content_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return WebPage.from_dict(data)
