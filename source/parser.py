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
    def _should_download_image(tag) -> bool:
        src = tag.get("src", "")
        if not src:
            return False

        # 1. Skip empty or obviously tracking images
        if src.startswith("data:") or "1x1" in src or "pixel" in src:
            return False

        # 2. Skip Wikipedia math renderings (SVG formulas)
        if "/render/svg/" in src or "/render/png/" in src:
            return False

        # 4. Skip tiny images (if width/height are present and very small)
        width = tag.get("width")
        height = tag.get("height")
        try:
            if width and int(width) < 50:
                return False
            if height and int(height) < 50:
                return False
        except (ValueError, TypeError):
            pass  # width/height may be strings like "100%" – ignore

        # 5. Skip obvious UI icons (common class names)
        classes = tag.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        icon_classes = {"icon", "logo", "spacer", "mw-logo", "noviewer", "mw-ui-icon"}
        if any(cls in icon_classes for cls in classes):
            return False

        # 6. If it has a `srcset` with small sizes, skip (but keep large versions)
        #    Not necessary for a first pass.

        return True

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

                if href.startswith(("javascript:", "mailto:", "#")):
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

                if not HTMLParser._should_download_image(tag):
                    continue   # skip this image entirely

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