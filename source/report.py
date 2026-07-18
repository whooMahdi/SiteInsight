from source.page import GalleryPage, ArticlePage, ProductPage, WebPage
from source.sitemap import SitemapGraph
from pathlib import Path

class ReportGenerator:
    def __init__(self, all_pages : set[WebPage], main_page: WebPage, failed_pages: int, time_seconds: float, output_dir: str):
        self._graph: SitemapGraph = SitemapGraph.from_webpages(all_pages)
        self._output_dir: str = output_dir
        self._main_page : WebPage = main_page

        self.failed_pages = failed_pages
        self.time_seconds = time_seconds

        self._sitemap_report_cache: str | None = None
        self._ranks_report_cache: str | None = None

        self._article_count = self._gallery_count = self._product_count = 0
        for p in all_pages:
            if isinstance(p, GalleryPage):
                self._gallery_count += 1
            elif isinstance(p, ArticlePage):
                self._article_count += 1
            elif isinstance(p, ProductPage):
                self._product_count += 1

        self._pages_crawled = len(all_pages)

    def _sitemap_report(self) -> str:
        if self._sitemap_report_cache is None:
            self._sitemap_report_cache = self._graph.make_sitemap_tree_summurized(self._main_page) + "\n\n" + self._graph.to_text()
        return self._sitemap_report_cache

    def _ranks_report(self) -> str:
        if self._ranks_report_cache is None:
            self._ranks_report_cache = self._graph.to_ranks_text()
        return self._ranks_report_cache

    def _write_report(self, filename: str, content: str):
        file_path = Path(self._output_dir, filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open(mode="w", encoding="utf-8") as f:
            f.write(content)

    def write_sitemap_file(self):
        self._write_report("sitemap.txt", self._sitemap_report())

    def write_pagerank_file(self) -> None:
        self._write_report("pagerank.txt", self._ranks_report())

    def generate_final_report(self) -> str:
        return f"""FINAL REPORT :
----------------------------
"pages_crawled"  : {self._pages_crawled}

"articles"       : {self._article_count}
"products"       : {self._product_count}
"galleries"      : {self._gallery_count}

"failed_pages"   : {self.failed_pages}
"time_seconds"   : {self.time_seconds:.2f}
"""

    def write_final_report(self):
        self._write_report("report.txt", self.generate_final_report())