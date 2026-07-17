from urllib.parse import urljoin
from bs4 import BeautifulSoup
from source.url_utils import URL
from source.page import (
    WebPage,
    PageContent,
    PageFactory,
)


class HTMLParser:
    @staticmethod
    def parse(html_content: str, base_url: URL) -> WebPage:
        soup = BeautifulSoup(html_content, "lxml")

        title = HTMLParser._extract_title(soup)
        content = HTMLParser._extract_content(soup, base_url)

        return PageFactory.create_page(
            url=base_url,
            page_title=title,
            content=content,
        )

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        title = soup.find("title")
        return title.get_text(strip=True) if title else "No title"

    @staticmethod
    def _extract_content(
        soup: BeautifulSoup,
        base_url: URL,
    ) -> PageContent:
        content = PageContent()

        for tag in soup.find_all(["a", "p", "img"]):

            if tag.name == "a":
                href = tag.get("href")
                if not href:
                    continue

                if href.startswith((
                    "#",
                    "javascript:",
                    "mailto:",
                    "tel:",
                    "sms:",
                    "data:",
                    "blob:",
                    "about:",
                    "file:",
                    "ftp:",
                    "ws:",
                    "wss:",
                    "intent:",
                    "market:",
                    "geo:",
                    "maps:",
                    "android-app:",
                    "tg:",
                    "whatsapp:",
                    "viber:",
                    "skype:",
                    "zoommtg:",
                    "slack:",
                    "discord:"
                )):
                    continue

                absolute = HTMLParser._absolute_url(href, base_url)
                text = tag.get_text(" ", strip=True) or None

                content.add_snippet(
                    PageContent.LinkSnippet(
                        link=str(absolute),
                        showtext=text,
                    )
                )

            elif tag.name == "p":
                text = tag.get_text(" ", strip=True)
                if text:
                    content.add_snippet(
                        PageContent.TextSnippet(text)
                    )

            elif tag.name == "img":
                src = tag.get("src")
                if not src:
                    continue

                absolute = HTMLParser._absolute_url(src, base_url)
                alt = tag.get("alt", "").strip() or None

                content.add_snippet(
                    PageContent.ImageSnippet(
                        image_url=str(absolute),
                        image_local_path=None,
                        description=alt,
                    )
                )

            elif tag.name == "video":
                pass # optional feature

        return content

    @staticmethod
    def _absolute_url(url: str, base_url: URL) -> URL:
        return URL(urljoin(str(base_url), url))