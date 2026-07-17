from pathlib import Path
from source.url_utils import URL
from source.config import AppConfig
from source.crawler import Crawler


config = AppConfig()
config.load_from_file("config.json")
config.start_url = URL("wikipedia.com/wiki/crawler").value
print(f"Starting crawler on: {config.start_url}")

crawler = Crawler(config)
try:
    crawled_pages = crawler.crawl()

    print("\n" + "=" * 70)
    print("Test finished successfully!")
    print("Crawl Statistics:")
    print(f"   Total successfully crawled pages: {len(crawled_pages)}")
    print(f"   Failed pages (network/HTTP errors): {crawler.failed_pages}")
    print(f"   Saved output path: {Path(config.output_dir).resolve()}")
    print("=" * 70)

# except KeyboardInterrupt:
#     print("\nTest Interrupted.")
except Exception:
    print("\nTest failed with an error:")
    import traceback
    traceback.print_exc()
