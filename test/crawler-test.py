import sys
from pathlib import Path

# Add the current directory to the system path to prevent import errors
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

try:
    from source.config import AppConfig
    from source.crawler import Crawler
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure this file is placed in the project root directory (parent of 'source').")
    sys.exit(1)


class TestConfig(AppConfig):
    """A custom configuration class for quick crawler testing without modifying the main config."""
    def __init__(self, start_url: str):
        # Call the parent constructor if it expects specific arguments
        super().__init__()
        
        self.start_url = start_url
        self.output_dir = "test_archive"  # Save test results in a separate directory
        self.max_depth = 2                # Test crawl depth
        self.thread_count = 4             # Number of threads for fetching pages
        self.images_threads_count = 3     # Number of threads for downloading images
        self.timeout = 10                 # Request timeout in seconds
        self.proxy_url = None             # Set proxy URL if needed


def run_test():
    # Target URL to start the test crawl
    test_url = "https://roocket.ir/articles/two-factor-authentication/"
    
    print("=" * 70)
    print(f"🚀 Starting multi-threaded crawler test on:")
    print(f"   👉 {test_url}")
    print("=" * 70)

    # Initialize config and instantiate the crawler
    config = TestConfig(start_url=test_url)
    crawler = Crawler(config)

    try:
        # Run the crawler
        crawled_pages = crawler.crawl()

        # Print summary statistics after finishing the crawl
        print("\n" + "=" * 70)
        print("✅ Test finished successfully!")
        print(f"📊 Crawl Statistics:")
        print(f"   🔹 Total successfully crawled pages: {len(crawled_pages)}")
        print(f"   🔸 Failed pages (network/HTTP errors): {crawler.failed_pages}")
        print(f"   📁 Saved output path: {Path(config.output_dir).resolve()}")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user.")
    except Exception as e:
        print(f"\n❌ Test failed with an error:")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_test()