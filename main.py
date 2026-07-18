import argparse
import sys
from pathlib import Path

from source import AppConfig, Crawler, run_tui


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SiteInsight : Web crawler")
    parser.add_argument("--set", "-s", action="store_true",
                    help="Just set values in the config file, dont crawl")

    parser.add_argument("--gui", "-g", action="store_true",
                    help="Force launch the interactive TUI mode")

    parser.add_argument("--url", "-u", help="Starting URL (overrides config)")
    parser.add_argument("--depth", "-d", help="How much depth gooing deep into the website")
    parser.add_argument("--max-links", "-ml", help="Maximum links in a page to fetch an go deeper")
    parser.add_argument("--threads", "-t", help="Threads count for fetching and crawling pages")
    parser.add_argument("--threads-image", "-ti", help="Threads count for downloading page images")
    parser.add_argument("--output", "-o", help="Output dir for the output pages and reports")
    parser.add_argument("--proxy", "-p", help="Proxy for hiding your ip or accessing blocked websites or vpn")
    parser.add_argument("--time-out", "-to", help="Maximum time limit for fetching one page in seconds")

    parser.add_argument("--web", action="store_true",
                    help="Serve the TUI over a browser (localhost) instead of running it in this terminal")
    parser.add_argument("--host", default="localhost", help="Host to bind the web server to (with --web)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the web server to (with --web)")
    return parser


def apply_args(config: AppConfig, args: argparse.Namespace) -> None:
    if args.url is not None:
        config.start_url = str(args.url)
    if args.depth is not None:
        config.max_depth = int(args.depth)
    if args.max_links is not None:
        config.max_links_per_page = int(args.max_links)
    if args.threads is not None:
        config.threads_count = int(args.threads)
    if args.threads_image is not None:
        config.image_threads_count = int(args.threads_image)
    if args.output is not None:
        config.output_dir = str(args.output)
    if args.proxy is not None:
        config.proxy_url = str(args.proxy)
    if args.time_out is not None:
        config.timeout = int(args.time_out)


def run_headless(config: AppConfig, args: argparse.Namespace) -> None:
    apply_args(config, args)
    config.save_to_file()

    # check if need crawl or just setting configs
    if args.set:
        return

    crawler = Crawler(config)
    try:
        crawler.crawl()
        print("Crawling is completed!")
    except KeyboardInterrupt:
        print("interrupted by user.")
    except Exception as e:
        print(f"\nfailed with error: \n{e}")


def run_web(host: str, port: int) -> None:
    try:
        from textual_serve.server import Server
    except ImportError:
        print("The --web flag needs the 'textual-serve' package: poetry add textual-serve")
        sys.exit(1)

    # Runs this same file (with no flags) as the command each browser
    # connection spawns — no-flags is exactly what launches the TUI below.
    command = f"{sys.executable} {Path(__file__).resolve()}"
    server = Server(command, host=host, port=port)
    print(f"Serving SiteInsight at http://{host}:{port}")
    server.serve()


def main():
    AppConfig.create_default_config_file()
    default_conf = AppConfig.create_from_file()

    parser = build_arg_parser()
    args = parser.parse_args()

    # If --gui is set, apply any other provided arguments to config and run TUI immediately.
    if args.gui:
        apply_args(default_conf, args)
        run_tui(default_conf)
        return

    if args.web:
        run_web(args.host, args.port)
        return

    run_headless(default_conf, args)


if __name__ == "__main__":
    main()