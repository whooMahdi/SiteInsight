from abc import ABC, abstractmethod
from typing import Optional

CHARACTER_PER_IMAGE_RATIO = 380

class PageContent:
    class ContentSnippet(ABC):
        @property
        @abstractmethod
        def text_on_image_weight(self) -> tuple[float, float]:
            pass

    class ImageSnippet(ContentSnippet):
        def __init__(self, image_url: str, description : Optional[str] = None):
            self.image_url: str = image_url
            self.description: Optional[str] = description
        @property
        def text_on_image_weight(self) -> tuple[float, float]:
            return (0 , 1)

    class TextSnippet(ContentSnippet):
        def __init__(self, text: str):
            self.text: str = text
        @property
        def text_on_image_weight(self) -> tuple[float, float]:
            r = len(self.text) // CHARACTER_PER_IMAGE_RATIO
            return (r, r)

    class LinkSnippet(ContentSnippet):
        def __init__(self, link: str):
            self.link: str = link
        @property
        def text_on_image_weight(self) -> tuple[float, float]:
            return (0.25, 1)

    def __init__(self, snippet_list: Optional[list[ContentSnippet]] = None):
        self._snippet_list: list[PageContent.ContentSnippet] = snippet_list or list()

    def add_snippet(self, snippet: ContentSnippet):
        self._snippet_list.append(snippet)

    @property
    def total_text_on_image_weight(self) -> float:
        num = 0.0
        denom = 0.0

        for s in self._snippet_list:
            w = s.text_on_image_weight
            num += w[0]
            denom += w[1]

        return num / denom

class WebPage:
    def __init__(self, url: str, page_title: str, content: PageContent, raw_html: str, links: list['WebPage'], refered_in: list['WebPage']) -> None:
        self.url: str = url
        self.page_title: str = page_title
        self.content: PageContent = content
        self.raw_html: str = raw_html
        self.links: list[WebPage]

# class ArticlePage(WebPage):
# def __init__(self, url: str, html_content: str, depth: int, author: Optional[str] =
# None) -> None:
# super().__init__(url, html_content, depth)
# self.author: Optional[str] = author
# self.category = "article"
# class ProductPage(WebPage):
# def __init__(self, url: str, html_content: str, depth: int, price: Optional[str] =
# None) -> None:
# super().__init__(url, html_content, depth)
# self.price: Optional[str] = price
# self.category = "product"
# class GalleryPage(WebPage):
# def __init__(self, url: str, html_content: str, depth: int, image_urls:
# Optional[List[str]] = None) -> None:
# super().__init__(url, html_content, depth)
# self.image_urls: List[str] = image_urls or []
# self.category = "gallery"
# class PageFactory:
# @staticmethod
# def create_page(url: str, html_content: str, depth: int, image_count: int,
# contains_price: bool) -> WebPage:
# pass