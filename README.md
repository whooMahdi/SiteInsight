# SiteInsight — Web Crawler

A multi-threaded website crawler that walks a single domain, classifies each
page it finds (article / product / gallery), pulls down its images, and
produces a sitemap + PageRank-style ranking + summary report at the end.

It stays inside the starting domain, respects `robots.txt`, and saves every
page as structured JSON rather than raw HTML.

## Table of contents

- [SiteInsight — Web Crawler](#siteinsight--web-crawler)
  - [Table of contents](#table-of-contents)
  - [Project structure](#project-structure)
  - [Setup](#setup)
  - [Configuration](#configuration)
  - [Usage](#usage)
  - [How it works](#how-it-works)
  - [Output layout](#output-layout)
  - [Notes / limitations](#notes--limitations)

## Project structure

```
.
├── main.py                 # entry point — CLI over AppConfig, then runs the crawler
├── config.json              # crawl settings (created on first run if missing)
├── requirements.txt
├── source
│   ├── __init__.py           # re-exports AppConfig, Crawler, URL, WebPage, etc.
│   ├── config.py             # AppConfig: load/save settings from config.json
│   ├── url_utils.py           # URL: normalization, comparison, hashing
│   ├── network.py             # SecurityLayer: robots.txt + same-domain checks
│   ├── parser.py              # HTMLParser: turns raw HTML into a PageContent
│   ├── page.py                # WebPage / PageContent / PageFactory (page classification)
│   ├── sitemap.py             # SitemapGraph: link graph + PageRank
│   ├── report.py              # ReportGenerator: sitemap.txt, pagerank.txt, report.txt
│   ├── crawler.py             # Crawler: the threaded fetch/parse/save pipeline
│   └── utils.py               # small helpers (path resolution, string shortening)
└── test
    └── crawler-test.py        # standalone script to run the crawler against a real URL
```

## Setup

The project is managed with [Poetry](https://python-poetry.org/).

```zsh
curl -sSL https://install.python-poetry.org | python3 -
```

Then, from the project root:

```zsh
poetry install
```

This creates a virtual environment and installs everything from
`pyproject.toml` — `requests`, `beautifulsoup4`, `lxml`, `fake-useragent`,
and `anytree`.

## Configuration

Settings live in `config.json`, loaded through `AppConfig`. If the file
doesn't exist yet, `main.py` creates a default one automatically on first
run.

```json
{
    "start_url": "https://example.com",
    "max_depth": 10,
    "max_links_per_page": 10,
    "threads_count": 5,
    "image_threads_count": 2,
    "output_dir": "output",
    "proxy_url": null,
    "timeout": 5
}
```

| Key                   | Meaning                                                           |
|------------------------|--------------------------------------------------------------------|
| `start_url`            | Where the crawl begins — also defines the domain it stays inside   |
| `max_depth`            | How many link-hops away from `start_url` the crawler will follow   |
| `max_links_per_page`   | Cap on how many *new* links get queued from a single page          |
| `threads_count`        | Number of page-fetching worker threads                             |
| `image_threads_count`  | Number of image-downloading worker threads                         |
| `output_dir`           | Where crawled pages, images, and reports get written                |
| `proxy_url`            | Optional proxy for outgoing requests                                |
| `timeout`              | Request timeout in seconds                                         |

## Usage

`main.py` is a thin CLI wrapper around `AppConfig`. Any flag you pass
overrides the matching value in `config.json` **and gets saved back to it**,
so an override sticks around as the new default for the next run too.

```zsh
poetry run python main.py [options]
```

| Flag                    | Short  | Meaning                                                  |
|--------------------------|--------|-------------------------------------------------------------|
| `--url`                  | `-u`   | Starting URL (overrides config)                             |
| `--depth`                | `-d`   | How deep to follow links from the start URL                 |
| `--max-links`            | `-ml`  | Max new links to queue per page                              |
| `--threads`              | `-t`   | Thread count for fetching pages                              |
| `--threads-image`        | `-ti`  | Thread count for downloading images                          |
| `--output`                | `-o`   | Output directory for pages and reports                       |
| `--proxy`                 | `-p`   | Proxy URL for the crawler's requests                         |
| `--time-out`              | `-to`  | Per-request timeout, in seconds                              |
| `--set`                   | `-s`   | Only write the values above to `config.json` — don't crawl   |

Run a crawl with one-off overrides:

```zsh
poetry run python main.py -u https://example.com -d 3 -t 8
```

Just update the saved config without crawling (useful for setting things
like `proxy_url` once and forgetting about it):

```zsh
poetry run python main.py -s -p http://127.0.0.1:8080
```

Run with whatever is already saved in `config.json`:

```zsh
poetry run python main.py
```

## How it works

1. **Fetching** — a pool of fetcher threads pulls URLs off a shared queue,
   requests each page (`requests`, with a rotating user-agent from
   `fake-useragent`), and hands the HTML to `HTMLParser`.
2. **Parsing** — `HTMLParser` walks the page with BeautifulSoup and extracts
   links, paragraph text, and images into a `PageContent` object.
3. **Classifying** — `PageFactory` looks at keyword hits in the URL/title/text
   and image count to decide whether the page is an `ArticlePage`,
   `ProductPage`, or `GalleryPage`.
4. **Filtering links** — before a page's outgoing links get queued,
   `SecurityLayer` checks them against `robots.txt` and the starting domain.
   Already-visited links are skipped so `max_links_per_page` is only spent on
   genuinely new URLs.
5. **Images** — each page's images go on a separate queue and are downloaded
   by their own thread pool; a page is only written to disk once all of its
   images have finished (or failed).
6. **Reporting** — once the queues drain, `SitemapGraph` builds a link graph
   over every crawled page, runs a PageRank-style scoring pass, and
   `ReportGenerator` writes `sitemap.txt`, `pagerank.txt`, and `report.txt`
   into the output directory.

## Output layout

```
output
├── article
│   └── example.com_some-page
│       ├── content.json
│       └── images
│           └── photo1.jpg
├── product
│   └── example.com_shop_item-42
│       ├── content.json
│       └── images
├── gallery
│   └── ...
├── sitemap.txt
├── pagerank.txt
└── report.txt
```

Each `content.json` holds the page's URL, title, type, and every extracted
snippet (text, links, images) so a crawl can be inspected or reprocessed
without re-fetching the site.

## Notes / limitations

- Crawling is restricted to the domain of `start_url` — external links are
  recorded but never followed.
- If `robots.txt` can't be fetched, the crawler falls back to allowing
  everything rather than blocking the crawl.
- Page classification (article/product/gallery) is a simple keyword +
  media-count heuristic, not a trained model — it works well enough for most
  sites but isn't perfect on unusual layouts.
- PageRank scores are only meaningful relative to *this* crawl's link graph,
  not the web at large.
- CLI overrides are written straight back to `config.json` on every run —
  there's no "just this once" flag, so double-check flags before running if
  you don't want them to become the new default.