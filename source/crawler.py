import json
import queue
import threading
import time
from pathlib import Path
from typing import List, Set, Optional

import requests
from fake_useragent import UserAgent

from source.config import AppConfig
from source.network import SecurityLayer
from source.parser import HTMLParser
from source.page import WebPage, PageContent
from source.report import ReportGenerator
from source.url_utils import URL


class Crawler:
    """Multi-threaded web crawler with image downloading and report generation."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.start_url = URL(config.start_url)

        # Output directory setup
        self.output_dir = Path(config.output_dir) if hasattr(config, "output_dir") else Path("archive")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Security layer initialization
        self.security = SecurityLayer(config)

        # Thread-safe data structures
        self.visited_lock = threading.Lock()
        self.visited_urls: Set[URL] = set()

        self.pages_lock = threading.Lock()
        self.pages: List[WebPage] = []

        self.failed_pages = 0
        self.failed_lock = threading.Lock()

        # Queue and flow control variables
        self.url_queue = queue.Queue()
        self.running = True
        self.active_fetchers = 0
        self.active_lock = threading.Lock()

        # Image management queues
        self.image_queue = queue.Queue()
        self.pages_to_save: dict[URL, WebPage] = {}
        self.pages_to_save_lock = threading.Lock()
        
        # Track pending image downloads per page
        self.pending_images_count: dict[URL, int] = {}
        self.pending_images_lock = threading.Lock()

        # Timing statistics
        self.start_time = None
        self.end_time = None

    def _sanitize_path(self, url: URL) -> str:
        """Generates a safe folder name from a URL."""
        import re
        name = str(url).replace("https://", "").replace("http://", "")
        name = re.sub(r'[^a-zA-Z0-9\-_.]', '_', name)
        if len(name) > 200:
            name = name[:200]
        return name

    def _fetch_page(self, url: URL, depth: int) -> Optional[WebPage]:
        """Fetches, parses, and extracts links from a single page."""
        try:
            ua = UserAgent().random
            proxy = self.config.proxy_url if hasattr(self.config, "proxy_url") else None
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            response = requests.get(
                url.value,
                headers={"User-Agent": ua},
                timeout=self.config.timeout if hasattr(self.config, "timeout") else 10,
                proxies=proxies,
            )
            
            if response.status_code != 200:
                print(f"[HTTP {response.status_code}] {url}")
                with self.failed_lock:
                    self.failed_pages += 1
                return None

            # Parse HTML content
            webpage = HTMLParser.parse(response.text, url)
            
            with self.pages_lock:
                self.pages.append(webpage)

            extracted_links = webpage.page_unique_urls
            print(f"[Crawler] Found {len(extracted_links)} unique links on {url.value}")

            # Enqueue new links if depth limit is not reached
            if depth < self.config.max_depth:
                # اعمال محدودیت max_links_per_page که تعریف شده بود ولی قبلاً هیچ‌جا اعمال نمی‌شد
                max_links = getattr(self.config, "max_links_per_page", None)
                links_to_process = (
                    list(extracted_links)[:max_links] if max_links else extracted_links
                )
                for link in links_to_process:
                    with self.visited_lock:
                        if link in self.visited_urls:
                            continue
                        
                        # Verify domain and safety constraints
                        is_allowed = self.security.should_crawl(link, self.visited_urls)
                        if is_allowed:
                            self.visited_urls.add(link)
                            self.url_queue.put((link, depth + 1))
                            print(f"  -> Added to Queue: {link.value}")
                        else:
                            # Useful debugging statement to inspect filter results
                            print(f"  X Skipped (Domain/Robots constraints): {link.value}")
            else:
                print(f"[Crawler] Max depth ({self.config.max_depth}) reached for {url.value}")

            # Send page images to image download queue
            self._enqueue_image_downloads(webpage)
            return webpage

        except Exception as e:
            print(f"[ERROR] Fetching page {url}: {e}")
            with self.failed_lock:
                self.failed_pages += 1
            return None

    def _enqueue_image_downloads(self, webpage: WebPage):
        """Prepares and pushes webpage images to the download workers."""
        pending_images = webpage.content.pending_download_image_snippets
        if not pending_images:
            self._save_page(webpage)
            return

        with self.pages_to_save_lock:
            self.pages_to_save[webpage.url] = webpage

        with self.pending_images_lock:
            self.pending_images_count[webpage.url] = len(pending_images)

        for snippet in pending_images:
            self.image_queue.put((webpage, snippet))

    def _download_image(self, webpage: WebPage, snippet: PageContent.ImageSnippet):
        """Downloads a single image and tracks relative path mapping."""
        try:
            page_folder = self.output_dir / webpage.page_type / self._sanitize_path(webpage.url)
            images_folder = page_folder / "images"
            images_folder.mkdir(parents=True, exist_ok=True)

            import re
            from urllib.parse import urlparse
            parsed = urlparse(snippet.image_url)
            filename = Path(parsed.path).name or "image.jpg"
            filename = re.sub(r'[^a-zA-Z0-9\-_.]', '_', filename)
            local_path = images_folder / filename

            ua = UserAgent().random
            resp = requests.get(
                snippet.image_url,
                headers={"User-Agent": ua},
                timeout=10,
                stream=True
            )
            
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                rel_path = local_path.relative_to(page_folder)
                snippet.image_local_path = str(rel_path)
                print(f"  Downloaded Image: {snippet.image_url} -> {rel_path}")
            else:
                print(f"  Failed to download image {snippet.image_url} (HTTP {resp.status_code})")

        except Exception as e:
            print(f"  Error downloading image {snippet.image_url}: {e}")

        finally:
            # Atomic operation to track pending image tasks
            should_save = False
            with self.pending_images_lock:
                if webpage.url in self.pending_images_count:
                    self.pending_images_count[webpage.url] -= 1
                    if self.pending_images_count[webpage.url] <= 0:
                        should_save = True
                        del self.pending_images_count[webpage.url]

            if should_save:
                # مهم: _save_page خودش هم pages_to_save_lock رو می‌گیره،
                # پس نباید در حالی که این قفل رو گرفتیم صداش بزنیم (وگرنه دِدلاک می‌شه).
                # فقط مقدار رو زیر قفل می‌خونیم و بعد از رها شدن قفل، ذخیره می‌کنیم.
                with self.pages_to_save_lock:
                    page = self.pages_to_save.get(webpage.url)
                if page:
                    self._save_page(page)

    def _save_page(self, webpage: WebPage):
        """Persists the crawled data into local JSON archives."""
        page_folder = self.output_dir / webpage.page_type / self._sanitize_path(webpage.url)
        page_folder.mkdir(parents=True, exist_ok=True)

        json_path = page_folder / "content.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(webpage.to_dict(), f, indent=4, ensure_ascii=False)

        with self.pages_to_save_lock:
            if webpage.url in self.pages_to_save:
                del self.pages_to_save[webpage.url]

    def _fetcher_worker(self):
        """Worker thread to consume URLs from the queue."""
        while self.running:
            try:
                url, depth = self.url_queue.get(timeout=1)
            except queue.Empty:
                with self.active_lock:
                    if self.active_fetchers == 0 and self.url_queue.empty():
                        break
                continue

            with self.active_lock:
                self.active_fetchers += 1

            self._fetch_page(url, depth)

            self.url_queue.task_done()
            with self.active_lock:
                self.active_fetchers -= 1

    def _image_worker(self):
        """Worker thread to consume images from the download queue."""
        while self.running or not self.image_queue.empty():
            try:
                webpage, snippet = self.image_queue.get(timeout=1)
            except queue.Empty:
                continue
            self._download_image(webpage, snippet)
            self.image_queue.task_done()

    def crawl(self) -> List[WebPage]:
        """Launches the multi-threaded crawling orchestration."""
        self.start_time = time.time()

        with self.visited_lock:
            self.visited_urls.add(self.start_url)
        self.url_queue.put((self.start_url, 0))

        # Thread counts setup
        fetcher_count = self.config.threads_count if hasattr(self.config, "threads_count") else 3
        image_workers = self.config.image_threads_count if hasattr(self.config, "image_threads_count") else 2

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=fetcher_count) as fetcher_executor:
            fetcher_futures = [
                fetcher_executor.submit(self._fetcher_worker)
                for _ in range(fetcher_count)
            ]

            with ThreadPoolExecutor(max_workers=image_workers) as image_executor:
                image_futures = [
                    image_executor.submit(self._image_worker)
                    for _ in range(image_workers)
                ]

                # Wait for the page crawler queue to fully clear
                self.url_queue.join()

                # Signal workers to shut down
                self.running = False

                for f in as_completed(fetcher_futures):
                    try:
                        f.result()
                    except Exception as e:
                        print(f"Fetcher thread error: {e}")
                        import traceback
                        traceback.print_exc()

                # Wait for pending images to download
                self.image_queue.join()

                for f in as_completed(image_futures):
                    try:
                        f.result()
                    except Exception as e:
                        print(f"Image worker thread error: {e}")
                        import traceback
                        traceback.print_exc()

        self.end_time = time.time()

        # Generate output sitemaps and reports
        self._generate_reports()

        return self.pages

    def _generate_reports(self):
        """Triggers report writing for final metrics, page rank and text sitemap."""
        if not self.pages:
            print("No pages crawled; skipping report generation.")
            return

        main_page = next((p for p in self.pages if p.url == self.start_url), self.pages[0])

        report_gen = ReportGenerator(
            all_pages=set(self.pages),
            main_page=main_page,
            failed_pages=self.failed_pages,
            time_seconds=self.end_time - self.start_time,
            output_dir=str(self.output_dir)
        )

        report_gen.write_sitemap_file()
        report_gen.write_pagerank_file()
        report_gen.write_final_report()
        print(f"\nReports successfully generated in: {self.output_dir}/")
        print(report_gen.generate_final_report())