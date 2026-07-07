from source.config import AppConfig
from source.network import SecurityLayer

conf = AppConfig("https://www.github.com")
sec = SecurityLayer(conf)
visited_urls = []

urls = [
    "https://github.com/gist/",
    "https://www.github.com/",
    "https://google.com/",
    "https://zoomit.ir/",
    "https://github.com/account-login",
    "https://github.com/"
]

for url in urls:
    if status := sec.should_crawl(url, visited_urls):
        visited_urls.append(url)

    print(f"URL: {url} -> {status}")