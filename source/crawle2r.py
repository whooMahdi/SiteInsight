# source/crawler.py

import json
import queue
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Set, Optional, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from source.config import AppConfig
from source.network import SecurityLayer
from source.parser import HTMLParser
from source.page import WebPage, PageContent
from source.report import ReportGenerator
from source.url_utils import URL


class Crawler:
    """Multi‑threaded web crawler with image downloading and report generation."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.start_url = URL(config.start_url)

        self.output_dir = Path(getattr(config, "output_dir", "archive"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.security = SecurityLayer(config)

        self.visited_lock = threading.Lock()
        self.visited_urls: Set[URL] = set()

        self.pages_lock = threading.Lock()
        self.pages: List[WebPage] = []

        self.failed_pages = 0
        self.failed_lock = threading.Lock()

        self.max_pages = getattr(config, "max_pages", 50)
        self.pages_crawled = 0
        self.stop_crawling = False

        self.url_queue = queue.Queue()
        self.running = True
        self.active_fetchers = 0
        self.active_lock = threading.Lock()

        self.image_queue = queue.Queue()
        self.pages_to_save: Dict[URL, tuple[WebPage, Set[str]]] = {}
        self.pages_to_save_lock = threading.RLock()

        self.start_time = None
        self.end_time = None

        self.timeout = getattr(config, "timeout", 30)
        self.proxies = None
        if hasattr(config, "proxy_url") and config.proxy_url:
            self.proxies = {
                "http": config.proxy_url,
                "https": config.proxy_url,
            }

    @staticmethod
    def _random_ua() -> str:
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        ]
        return random.choice(ua_list)

    @staticmethod
    def _new_session() -> requests.Session:
        session = requests.Session()
        session.headers.update({"User-Agent": Crawler._random_ua()})
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _sanitize_path(self, url: URL) -> str:
        import re
        name = str(url).replace("https://", "").replace("http://", "")
        name = re.sub(r'[^a-zA-Z0-9\-_.]', '_', name)
        if len(name) > 200:
            name = name[:200]
        return name

    @staticmethod
    def _should_download_image(url_str: str) -> bool:
        if not url_str or url_str.startswith("data:"):
            return False
        skip_patterns = [
            "1x1", "pixel", "spacer", "logo", "icon",
            "mw-logo", "noviewer", "mw-ui-icon",
            "load.php", "thumb.php",
            "Special:CentralAutoLogin"
        ]
        lower = url_str.lower()
        for pat in skip_patterns:
            if pat in lower:
                return False
        if lower.endswith(".svg") and ("icon" in lower or "logo" in lower):
            return False
        return True

    # -------------------------------------------------------------------------
    # Your exact _fetch_page (with all checks) – we only replace self.session
    # with a local session for thread safety.
    # -------------------------------------------------------------------------
    def _fetch_page(self, url: URL, depth: int) -> Optional[WebPage]:
        """Fetch a single page, parse it, and return a WebPage object."""
        url_str = str(url) if hasattr(url, 'value') else str(url)
        if not url_str.startswith(('http://', 'https://')):
            print(f"[SKIP] Invalid URL scheme: {url_str}")
            return None

        try:
            session = self._new_session()
            session.headers.update({"User-Agent": self._random_ua()})

            response = session.get(
                url_str,
                timeout=self.timeout,
                proxies=self.proxies,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                print(f"[429] Rate limited on {url}. Waiting {retry_after}s...")
                time.sleep(retry_after)
                response = session.get(
                    url_str,
                    timeout=self.timeout,
                    proxies=self.proxies,
                )

            if response.status_code != 200:
                print(f"[HTTP {response.status_code}] {url}")
                with self.failed_lock:
                    self.failed_pages += 1
                    if self.failed_pages >= self.max_pages * 2:
                        self.stop_crawling = True
                return None

            webpage = HTMLParser.parse(response.text, url)
            with self.pages_lock:
                self.pages.append(webpage)
                self.pages_crawled = len(self.pages)

            if self.pages_crawled >= self.max_pages:
                self.stop_crawling = True
                return webpage

            if self.stop_crawling:
                return webpage

            if depth < self.config.max_depth:
                for link in webpage.page_unique_urls:
                    if link.scheme not in ("http", "https"):
                        continue

                    with self.visited_lock:
                        if link in self.visited_urls:
                            continue

                    if self.security.should_crawl(link, self.visited_urls):
                        with self.visited_lock:
                            if link not in self.visited_urls:
                                self.visited_urls.add(link)
                                self.url_queue.put((link, depth + 1))

            self._enqueue_image_downloads(webpage)
            return webpage

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"[ERROR] fetching {url}: {e}")
            with self.failed_lock:
                self.failed_pages += 1
                if self.failed_pages >= self.max_pages * 2:
                    self.stop_crawling = True
            return None
        except Exception as e:
            print(f"[ERROR] fetching {url}: {e}")
            with self.failed_lock:
                self.failed_pages += 1
                if self.failed_pages >= self.max_pages * 2:
                    self.stop_crawling = True
            return None

    # -------------------------------------------------------------------------
    # Image handling – fixed to avoid duplicate downloads per page.
    # -------------------------------------------------------------------------
    def _enqueue_image_downloads(self, webpage: WebPage):
        pending = webpage.content.pending_download_image_snippets
        filtered = [s for s in pending if self._should_download_image(s.image_url)]
        pending.clear()
        pending.update(filtered)

        if not filtered:
            self._save_page(webpage)
            return

        with self.pages_to_save_lock:
            self.pages_to_save[webpage.url] = (webpage, set())

        for snippet in filtered:
            self.image_queue.put((webpage, snippet))

    def _download_image(self, webpage: WebPage, snippet: PageContent.ImageSnippet):
        try:
            page_folder = self.output_dir / webpage.page_type / self._sanitize_path(webpage.url)
            images_folder = page_folder / "images"
            images_folder.mkdir(parents=True, exist_ok=True)

            import hashlib
            from urllib.parse import urlparse
            parsed = urlparse(snippet.image_url)
            path = Path(parsed.path)
            ext = path.suffix if path.suffix else ".jpg"
            url_hash = hashlib.md5(snippet.image_url.encode()).hexdigest()[:12]
            filename = f"{url_hash}{ext}"
            local_path = images_folder / filename

            session = self._new_session()
            resp = session.get(
                snippet.image_url,
                timeout=10,
                stream=True,
                proxies=self.proxies,
            )
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                rel_path = local_path.relative_to(page_folder)
                snippet.image_local_path = str(rel_path)
                print(f"  Downloaded: {snippet.image_url} -> {rel_path}")
            else:
                print(f"  Failed to download {snippet.image_url} (HTTP {resp.status_code})")
                snippet.image_local_path = None

        except Exception as e:
            print(f"  Error downloading {snippet.image_url}: {e}")
            snippet.image_local_path = None

        finally:
            with self.pages_to_save_lock:
                if webpage.url in self.pages_to_save:
                    page_data, processed = self.pages_to_save[webpage.url]
                    processed.add(snippet.image_url)
                    total = len(page_data.content.pending_download_image_snippets)
                    if len(processed) >= total:
                        self._save_page(webpage)
                        del self.pages_to_save[webpage.url]

    def _save_page(self, webpage: WebPage):
        page_folder = self.output_dir / webpage.page_type / self._sanitize_path(webpage.url)
        page_folder.mkdir(parents=True, exist_ok=True)

        json_path = page_folder / "content.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(webpage.to_dict(), f, indent=4, ensure_ascii=False)

        with self.pages_to_save_lock:
            if webpage.url in self.pages_to_save:
                del self.pages_to_save[webpage.url]

    # -------------------------------------------------------------------------
    # Worker threads
    # -------------------------------------------------------------------------
    def _fetcher_worker(self):
        while self.running and not self.stop_crawling:
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
            time.sleep(random.uniform(0.5, 1.0))

            self.url_queue.task_done()
            with self.active_lock:
                self.active_fetchers -= 1

    def _image_worker(self):
        while self.running or not self.image_queue.empty():
            try:
                webpage, snippet = self.image_queue.get(timeout=1)
            except queue.Empty:
                continue
            self._download_image(webpage, snippet)
            self.image_queue.task_done()

    # -------------------------------------------------------------------------
    # Main crawl entry point – fixed wait loop to avoid hanging on stop.
    # -------------------------------------------------------------------------
    def crawl(self) -> List[WebPage]:
        self.start_time = time.time()

        self.url_queue.put((self.start_url, 0))

        fetcher_count = getattr(self.config, "thread_count", 3)
        image_workers = getattr(self.config, "images_threads_count", 2)

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

                # Wait until fetchers are done or we stop crawling.
                # Break if stop_crawling is True even if queue isn't empty.
                while True:
                    with self.active_lock:
                        if self.active_fetchers == 0 and (self.url_queue.empty() or self.stop_crawling):
                            break
                    time.sleep(0.5)

                # If we stopped early, clear the remaining tasks to prevent memory leaks.
                if self.stop_crawling and not self.url_queue.empty():
                    # Discard all remaining items in the URL queue
                    while not self.url_queue.empty():
                        try:
                            self.url_queue.get_nowait()
                            self.url_queue.task_done()
                        except queue.Empty:
                            break

                self.running = False

                for f in as_completed(fetcher_futures):
                    try:
                        f.result()
                    except Exception as e:
                        print(f"Fetcher error: {e}")

                # Wait for all image downloads to complete
                self.image_queue.join()
                self.running = False

                for f in as_completed(image_futures):
                    try:
                        f.result()
                    except Exception as e:
                        print(f"Image worker error: {e}")

        self.end_time = time.time()
        self._generate_reports()
        return self.pages

    def _generate_reports(self):
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
        print(f"\nReports written to {self.output_dir}/")
        print(report_gen.generate_final_report())




if __name__ == "__main__":
    main()