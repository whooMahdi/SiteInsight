import sys
from pathlib import Path

# Ensuring local source imports function correctly
sys.path.append(str(Path(__file__).resolve().parent))

from source.config import AppConfig
from source.crawler import Crawler


def get_user_inputs() -> AppConfig:
    print("=" * 60)
    print("🕸️  WELCOME TO THE MULTI-THREADED WEB CRAWLER  🕸️")
    print("=" * 60)
    
    # Get Starting URL
    while True:
        start_url = input("Enter starting URL (e.g., https://example.com): ").strip()
        if start_url:
            break
        print("❌ URL cannot be empty. Please try again.")

    # Get Max Depth with verification
    while True:
        depth_input = input("Enter max crawl depth [Default: 2]: ").strip()
        if not depth_input:
            max_depth = 2
            break
        try:
            max_depth = int(depth_input)
            if max_depth >= 0:
                break
            print("❌ Depth must be a non-negative integer.")
        except ValueError:
            print("❌ Invalid number. Please enter an integer.")

    # Get Thread Count for Pages
    while True:
        threads_input = input("Enter page fetcher thread count [Default: 4]: ").strip()
        if not threads_input:
            thread_count = 4
            break
        try:
            thread_count = int(threads_input)
            if thread_count > 0:
                break
            print("❌ Thread count must be greater than 0.")
        except ValueError:
            print("❌ Invalid number. Please enter an integer.")

    # Get Thread Count for Images
    while True:
        img_threads_input = input("Enter image downloader thread count [Default: 3]: ").strip()
        if not img_threads_input:
            images_threads_count = 3
            break
        try:
            images_threads_count = int(img_threads_input)
            if images_threads_count > 0:
                break
            print("❌ Image thread count must be greater than 0.")
        except ValueError:
            print("❌ Invalid number. Please enter an integer.")

    # Get Output Directory
    output_dir = input("Enter output directory [Default: archive]: ").strip()
    if not output_dir:
        output_dir = "archive"

    # Assemble and return config instance
    config = AppConfig()
    config.start_url = start_url
    config.max_depth = max_depth
    config.thread_count = thread_count
    config.images_threads_count = images_threads_count
    config.output_dir = output_dir
    config.timeout = 10  # Standard safety network timeout
    config.proxy_url = None

    return config


def main():
    try:
        config = get_user_inputs()
        
        print("\n" + "-" * 50)
        print("⚙️  Configuring Crawler with current parameters...")
        print(f"   • Start URL:    {config.start_url}")
        print(f"   • Max Depth:    {config.max_depth}")
        print(f"   • Page Threads: {config.thread_count}")
        print(f"   • Image Threads:{config.images_threads_count}")
        print(f"   • Output Dir:   {config.output_dir}")
        print("-" * 50 + "\n")

        crawler = Crawler(config)
        print("🚀 Crawling started...")
        results = crawler.crawl()
        print(f"🏁 Crawl session completed! Extracted {len(results)} pages successfully.")

    except KeyboardInterrupt:
        print("\n⚠️ Crawling aborted by the user.")
    except Exception as e:
        print(f"\n❌ Execution failed due to error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()