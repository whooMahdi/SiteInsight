import hashlib
import json
import queue
import random
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import requests
from fake_useragent import UserAgent

from source.config import AppConfig
from source.network import SecurityLayer
from source.parser import HTMLParser
from source.page import WebPage, PageContent
from source.report import ReportGenerator
from source.url_utils import URL
from source.utils import shortner

RANDOM_FROM_ALL_RATIO = 0.35

class Crawler:

    def __init__(self, config: AppConfig):
        self.config: AppConfig = config
        self.start_url: URL = URL(config.start_url)

        self.output_dir: Path = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.security: SecurityLayer = SecurityLayer(config)
        self.user_agent: UserAgent = UserAgent()

        self.visited_lock = threading.Lock()
        self.visited_urls: set[URL] = set()

        self.pages_lock = threading.Lock()
        self.pages: list[WebPage] = []

        self.failed_pages: int = 0
        self.failed_lock = threading.Lock()

        self.url_queue: queue.Queue = queue.Queue()
        self.running: bool = True
        self.active_fetchers: int = 0
        self.active_lock = threading.Lock()

        self.image_queue: queue.Queue = queue.Queue()
        self.pages_to_save: dict[URL, WebPage] = {}
        self.pages_to_save_lock = threading.Lock()

        self.pending_images_count: dict[URL, int] = {}
        self.pending_images_lock = threading.Lock()

        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        random.seed(time.time())

    def _sanitize_path(self, url: URL) -> str:
        name = str(url).replace("https://", "").replace("http://", "")
        name = re.sub(r'[^a-zA-Z0-9\-_.]', '_', name)

        if len(name) <= 200:
            return name

        suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        return name[:190] + "_" + suffix

    def _fetch_page(self, url: URL, depth: int) -> Optional[WebPage]:
        try:
            proxy = self.config.proxy_url
            proxies = {"http": proxy, "https": proxy} if proxy else None

            response = requests.get(
                url.value,
                headers={"User-Agent": self.user_agent.random},
                timeout=self.config.timeout,
                proxies=proxies,
            )

            if response.status_code != 200:
                print(f"[HTTP {response.status_code}] {shortner(url.value)}")
                with self.failed_lock:
                    self.failed_pages += 1
                return None

            webpage = HTMLParser.parse(response.text, url)

            with self.pages_lock:
                self.pages.append(webpage)

            extracted_links = webpage.page_unique_urls
            print(f"[Crawler] Found {len(extracted_links)} unique links on {shortner(url.value)}")

            def check_add_link_to_queue(link: URL) -> bool:
                if self.security.is_crawl_allowed(link):
                    allowed = False
                    with self.visited_lock:
                        if link not in self.visited_urls:
                            self.visited_urls.add(link)
                            allowed = True
                    if allowed:
                        self.url_queue.put((link, depth + 1))
                        print(f"  [+] Added to Queue: {shortner(link.value)}")
                        return True
                
                print(f"  [-] Skipped (Domain/Robots constraints/Currently visited): {shortner(link.value)}")
                
                return False


            if depth < self.config.max_depth:
                
                max_links = self.config.max_links_per_page
                random_links_count = int(RANDOM_FROM_ALL_RATIO * max_links)
                usual_links_count = max_links - random_links_count
                
                usual_queued = 0
                last_usual_i = -1
                for i in range(len(extracted_links)):
                    last_usual_i = i
                    link = extracted_links[i]
                    if check_add_link_to_queue(link):
                        usual_queued += 1
                    if usual_queued >= usual_links_count:
                        break
                
                # selecting random urls using (Sparse Dict Random Sampling) strategy for effciency
                # spare dict random sampling is a way to emulate Swap and Pop algorithem withou list of indexes

                random_queued = 0
                start = last_usual_i + 1
                end = len(extracted_links)
                remaining = end - start

                # key   = position in the conceptual array
                # value = actual index from extracted_links
                swap = dict()

                while remaining > 0 and random_queued < random_links_count:

                    pos = random.randrange(remaining)

                    # default is the position in extracted links
                    actual = swap.get(pos, start + pos)
        
                    last_pos = remaining - 1
                    last_actual = swap.get(last_pos, start + last_pos)

                    # swap
                    swap[pos] = last_actual
                    
                    # pop
                    if last_pos in swap:
                        del swap[last_pos]

                    link = extracted_links[actual]

                    if check_add_link_to_queue(link):
                        random_queued += 1

                    remaining -= 1

            else:
                print(f"[Crawler] Max depth ({self.config.max_depth}) reached for {shortner(url.value)}")

            self._enqueue_image_downloads(webpage)
            return webpage

        except Exception as e:
            print(f"[ERROR] Fetching page {shortner(url.value)}: {e}")
            with self.failed_lock:
                self.failed_pages += 1
            return None

    def _enqueue_image_downloads(self, webpage: WebPage):
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
        try:
            page_folder = self.output_dir / webpage.page_type / self._sanitize_path(webpage.url)
            images_folder = page_folder / "images"
            images_folder.mkdir(parents=True, exist_ok=True)

            parsed = urlparse(snippet.image_url)
            filename = Path(parsed.path).name or "image.jpg"
            filename = re.sub(r'[^a-zA-Z0-9\-_.]', '_', filename)
            local_path = images_folder / filename

            resp = requests.get(
                snippet.image_url,
                headers={"User-Agent": self.user_agent.random},
                timeout=10,
                stream=True,
            )

            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                rel_path = local_path.relative_to(page_folder)
                snippet.image_local_path = str(rel_path)
                print(f"  Downloaded Image: {shortner(snippet.image_url)} -> {shortner(str(rel_path))}")
            else:
                print(f"  Failed to download image {shortner(snippet.image_url)} (HTTP {resp.status_code})")

        except Exception as e:
            print(f"  Error downloading image {shortner(snippet.image_url)}: {e}")

        finally:
            should_save = False
            with self.pending_images_lock:
                if webpage.url in self.pending_images_count:
                    self.pending_images_count[webpage.url] -= 1
                    if self.pending_images_count[webpage.url] <= 0:
                        should_save = True
                        del self.pending_images_count[webpage.url]

            if should_save:
                with self.pages_to_save_lock:
                    page = self.pages_to_save.get(webpage.url)
                if page:
                    self._save_page(page)

    def _save_page(self, webpage: WebPage):
        page_folder = self.output_dir / webpage.page_type / self._sanitize_path(webpage.url)
        page_folder.mkdir(parents=True, exist_ok=True)

        json_path = page_folder / "content.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(webpage.to_dict(), f, indent=4, ensure_ascii=False)

        with self.pages_to_save_lock:
            if webpage.url in self.pages_to_save:
                del self.pages_to_save[webpage.url]

    def _fetcher_worker(self):
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
        while self.running or not self.image_queue.empty():
            try:
                webpage, snippet = self.image_queue.get(timeout=1)
            except queue.Empty:
                continue
            self._download_image(webpage, snippet)
            self.image_queue.task_done()

    def crawl(self) -> list[WebPage]:
        self.start_time = time.time()

        with self.visited_lock:
            self.visited_urls.add(self.start_url)
        self.url_queue.put((self.start_url, 0))

        fetcher_count = self.config.threads_count
        image_workers = self.config.image_threads_count

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

                self.url_queue.join()
                self.running = False

                for f in as_completed(fetcher_futures):
                    try:
                        f.result()
                    except Exception as e:
                        print(f"Fetcher thread error: {e}")
                        traceback.print_exc()

                self.image_queue.join()

                for f in as_completed(image_futures):
                    try:
                        f.result()
                    except Exception as e:
                        print(f"Image worker thread error: {e}")
                        traceback.print_exc()

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
            output_dir=str(self.output_dir),
        )

        report_gen.write_sitemap_file()
        report_gen.write_pagerank_file()
        report_gen.write_final_report()
        print(f"\n[~] Reports successfully generated in: {self.output_dir}/")
        print(report_gen.generate_final_report())