from source.config import AppConfig
from source.network import SecurityLayer
from source.url_utils import URL

conf = AppConfig("https://www.github.com")
sec = SecurityLayer(conf)
visited_urls = set()

urls = [
    "https://github.com/gist/",
    "https://www.github.com/",
    "https://google.com/",
    "https://zoomit.ir/",
    "https://github.com/account-login",
    "https://github.com/"
]

urls = map(URL, urls)

for url in urls:
    if status := sec.is_crawl_allowed(url) and url not in visited_urls:
        visited_urls.add(url)

    print(f"{url} -> {status}")
print(visited_urls)