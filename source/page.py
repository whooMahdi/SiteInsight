from abc import ABC, abstractmethod
from typing import Optional
from source.network import URL

CHARACTER_PER_IMAGE_RATIO = 380

class PageContent:
    class ContentSnippet(ABC):
        @property
        @abstractmethod
        def text_on_image_weight(self) -> tuple[float, float]:
            pass
        
        @property
        @abstractmethod
        def raw_text(self) -> str:
            pass

    class ImageSnippet(ContentSnippet):
        def __init__(self, image_url: str, description : Optional[str] = None):
            self.image_url: str = image_url
            self.description: Optional[str] = description
        @property
        def text_on_image_weight(self) -> tuple[float, float]:
            return (0 , 1)
        @property
        def raw_text(self) -> str:
            return self.image_url + (self.description or "")

    class VideoSnippet(ContentSnippet):
        def __init__(self, video_url: str, description : Optional[str] = None):
            self.video_url: str = video_url
            self.description: Optional[str] = description
        @property
        def text_on_image_weight(self) -> tuple[float, float]:
            return (0.2 , 1)
        @property
        def raw_text(self) -> str:
            return self.video_url + (self.description or "")

    class TextSnippet(ContentSnippet):
        def __init__(self, text: str):
            self.text: str = text
        @property
        def text_on_image_weight(self) -> tuple[float, float]:
            r = len(self.text) // CHARACTER_PER_IMAGE_RATIO
            return (r, r)
        @property
        def raw_text(self) -> str:
            return self.text

    class LinkSnippet(ContentSnippet):
        def __init__(self, link: str):
            self.link: str = link
        @property
        def text_on_image_weight(self) -> tuple[float, float]:
            return (0.25, 1)
        @property
        def raw_text(self) -> str:
            return self.link

    def __init__(self, snippet_list: Optional[list[ContentSnippet]] = None):
        self._snippet_list: list[PageContent.ContentSnippet] = snippet_list or list()
        self._link_snippet_list: list[PageContent.LinkSnippet] = 
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

class WebPage:
    def __init__(self, url: URL, page_title: str, content: PageContent):
        self.url: URL = url
        self.page_title: str = page_title
        self.content: PageContent = content
        self.refered_in: list['WebPage'] = list()     

    def add_refered_in(self, page: 'WebPage'):
        self.refered_in.append(page)

class ArticlePage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent, author: Optional[str] = None):
        super().__init__(url, page_title, content)
        self.author = author
        self.catigory_name = "[article]"            

class ProductPage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent, product_price: Optional[int] = None):
        super().__init__(url, page_title, content)
        self.product_price = product_price

class GalleryPage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent):
        super().__init__(url, page_title, content)

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
        return points

    @property
    def total_text_on_image_weight(self) -> float:
        num = 0.0
        denom = 0.0

        for s in self.content.get_page_snippets():
            w = s.text_on_image_weight
            num += w[0]
            denom += w[1]

        return num / denom
    
    @property
    def media_count(self):
        return len(list(self.content.get_media_snippets()))
    
    def create(self):
        gallery_point = ((0.4 if self.media_count > 10 else 0.0) + self.total_text_on_image_weight) * 
        if :
            return GalleryPage(self.url, self.page_title, self.content)
        elif self._similarity_points_in_text(["price", "product", "stock", "store"]) + self._similarity_points_in_url(["/p/", "product", "item"]) * 2 > 2:
    

    @staticmethod
    def create_page(url: URL, page_title: str, content: PageContent) -> WebPage:
        return PageFactory(url, page_title, content).create()
    