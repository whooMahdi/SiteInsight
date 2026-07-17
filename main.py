import argparse
from source import AppConfig, Crawler

def main():
    AppConfig.create_default_config_file()
    default_conf = AppConfig.create_from_file()

    parser = argparse.ArgumentParser(description="SiteInsight : Web crawler")
    parser.add_argument("--set", "-s", action="store_true", 
                    help="Just set values in the config file, dont crawl")

    parser.add_argument("--url", "-u", help="Starting URL (overrides config)")
    parser.add_argument("--depth", "-d", help="How much depth gooing deep into the website")
    parser.add_argument("--max-links", "-ml", help="Maximum links in a page to fetch an go deeper")
    parser.add_argument("--threads", "-t", help="Threads count for fetching and crawling pages")
    parser.add_argument("--threads-image", "-ti", help="Threads count for downloading page images")
    parser.add_argument("--output", "-o", help="Output dir for the output pages and reports")
    parser.add_argument("--proxy", "-p", help="Proxy for hiding your ip or accessing blocked websites or vpn")
    parser.add_argument("--time-out", "-to", help="Maximum time limit for fetching one page in seconds")

    args = parser.parse_args()

    if args.url is not None:
        default_conf.start_url = str(args.url)
    if args.depth is not None:
        default_conf.max_depth = int(args.depth)
    if args.max_links is not None:
        default_conf.max_links_per_page = int(args.max_links)
    if args.threads is not None:
        default_conf.threads_count = int(args.threads)
    if args.threads_image is not None:
        default_conf.image_threads_count = int(args.threads_image)
    if args.output is not None:
        default_conf.output_dir = str(args.output)
    if args.proxy is not None:
        default_conf.proxy_url = str(args.proxy)
    if args.time_out is not None:
        default_conf.timeout = int(args.time_out)

    default_conf.save_to_file()

    # check if need crawl or just setting configs
    if not args.set:
        crawler = Crawler(default_conf)

        try:
            crawled_pages = crawler.crawl()
 
            print("Crawling is completed!")
        except KeyboardInterrupt:
            print("interrupted by user.")
        except Exception as e:
            print(f"\nfailed with error: \n{e}")

if __name__ == "__main__":
    main()