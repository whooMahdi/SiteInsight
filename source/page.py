from abc import ABC, abstractmethod
from typing import Optional
from source.network import URL

CHARACTER_PER_IMAGE_RATIO = 380

class PageContent:
    class ContentSnippet(ABC):
        @property
        @abstractmethod
        def raw_text(self) -> str:
            pass

    class ImageSnippet(ContentSnippet):
        def __init__(self, image_url: str, description : Optional[str] = None):
            self.image_url: str = image_url
            self.description: Optional[str] = description
        @property
        def raw_text(self) -> str:
            return self.image_url + (self.description or "")

    class VideoSnippet(ContentSnippet):
        def __init__(self, video_url: str, description : Optional[str] = None):
            self.video_url: str = video_url
            self.description: Optional[str] = description
        @property
        def raw_text(self) -> str:
            return self.video_url + (self.description or "")

    class TextSnippet(ContentSnippet):
        def __init__(self, text: str):
            self.text: str = text
        @property
        def raw_text(self) -> str:
            return self.text

    class LinkSnippet(ContentSnippet):
        def __init__(self, link: str):
            self.link: str = link
        @property
        def raw_text(self) -> str:
            return self.link

    def __init__(self, snippet_list: Optional[list[ContentSnippet]] = None):
        self._snippet_list: list[PageContent.ContentSnippet] = snippet_list or list()
        self._link_snippet_list: list[PageContent.LinkSnippet] = \
            list() if snippet_list is None else list(filter(lambda x: isinstance(x, PageContent.LinkSnippet), snippet_list)) # type: ignore

    def add_snippet(self, snippet: ContentSnippet):
        if isinstance(snippet, PageContent.LinkSnippet):
            self._link_snippet_list.append(snippet)
        self._snippet_list.append(snippet)
    
    def get_page_snippets(self):
        for s in self._snippet_list:
            yield s
    
    @property
    def page_links_list(self):
        return self._link_snippet_list
    
    def get_media_snippets(self):
        for s in self.get_page_snippets():
            if isinstance(s, PageContent.ImageSnippet | PageContent.VideoSnippet):
                yield s

    def get_text_snippets(self):
        for s in self.get_page_snippets():
            if isinstance(s, PageContent.TextSnippet):
                yield s
class WebPage:
    def __init__(self, url: URL, page_title: str, content: PageContent):
        self.url: URL = url
        self.page_title: str = page_title
        self.content: PageContent = content
        self.refered_in: list['WebPage'] = list()     

    def add_refered_in(self, page: 'WebPage'):
        self.refered_in.append(page)

class ArticlePage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent, author_snippet: Optional[PageContent.ContentSnippet] = None):
        super().__init__(url, page_title, content)

        if author_snippet is None:
            for s in content.get_page_snippets():
                if "author" in s.raw_text:
                    author_snippet = s
        self.author_snippet = author_snippet

class ProductPage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent, price_snippet: Optional[PageContent.TextSnippet] = None):
        super().__init__(url, page_title, content)
        if price_snippet is None:
            for t in content.get_text_snippets():
                if "price" in t.text.lower():
                    price_snippet = t
        self.price_snippet = price_snippet

class GalleryPage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent):
        super().__init__(url, page_title, content)

    @property
    def media_snippets(self):
        return self.content.get_media_snippets()

class PageFactory():
    def __init__(self, url: URL, page_title: str, content: PageContent):
        self.url = url
        self.page_title = page_title
        self.content = content

    def _similarity_points_in_url(self, keywords: list[str]) -> int:
        points = 0
        for k in keywords:
            points += self.url.path.lower().count(k)
        return points

    def _similarity_points_in_text(self, keywords : list[str]) -> int:
        points = 0
        for snippet in self.content.get_page_snippets():
            text = snippet.raw_text.lower()
            for k in keywords:
                points += text.count(k.lower())
        titile_l = self.page_title.lower()
        for k in keywords:
            points += titile_l.count(k.lower())
        return points
    
    @property
    def media_count(self):
        return len(list(self.content.get_media_snippets()))
    
    def create(self):
        text_product_similarity = self._similarity_points_in_text(["price", "product", "stock", "store"])
        url_product_similarity = self._similarity_points_in_url(["/p/", "product", "item"])
        if text_product_similarity >= 2 or (text_product_similarity > 0 and url_product_similarity > 0):
            return ProductPage(self.url, self.page_title, self.content)
        elif self.media_count > 5 or self._similarity_points_in_url(["gallery"]) > 0 or self._similarity_points_in_text(["gallery"]) > 0:
            return GalleryPage(self.url, self.page_title, self.content)
        else:
            return ArticlePage(self.url, self.page_title, self.content)
    

    @staticmethod
    def create_page(url: URL, page_title: str, content: PageContent) -> WebPage:
        return PageFactory(url, page_title, content).create()
    