from abc import ABC, abstractmethod
from typing import Optional
from source.url_utils import URL

CHARACTER_PER_IMAGE_RATIO = 380

class PageContent:
    class ContentSnippet(ABC):
        @property
        @abstractmethod
        def raw_text(self) -> str:
            pass

        @abstractmethod
        def to_dict(self) -> dict:
            pass

        @staticmethod
        def from_dict(data: dict) -> 'PageContent.ContentSnippet':
            snippet_type = data.get("type")
            if snippet_type == "image":
                return PageContent.ImageSnippet(
                    image_url=data["image_url"],
                    image_local_path=data["image_local_path"],
                    description=data.get("description")
                )
            elif snippet_type == "video":
                return PageContent.VideoSnippet(
                    video_url=data["video_url"],
                    description=data.get("description")
                )
            elif snippet_type == "text":
                return PageContent.TextSnippet(text=data["text"])
            elif snippet_type == "link":
                return PageContent.LinkSnippet(link=data["link"], showtext=data["showtext"])
            else:
                raise ValueError(f"Unknown snippet type: {snippet_type}")

    class ImageSnippet(ContentSnippet):
        def __init__(self, image_url: str, image_local_path: Optional[str] = None, description : Optional[str] = None):
            self.image_url: str = image_url
            self.image_local_path = image_local_path
            self.description: Optional[str] = description
        @property
        def raw_text(self) -> str:
            return self.image_url + (self.description or "")
        def to_dict(self) -> dict:
            return {
                "type": "image",
                "image_url": self.image_url,
                "image_local_path": self.image_local_path,
                "description": self.description
            }

    class VideoSnippet(ContentSnippet):
        def __init__(self, video_url: str, description : Optional[str] = None):
            self.video_url: str = video_url
            self.description: Optional[str] = description
        @property
        def raw_text(self) -> str:
            return self.video_url + (self.description or "")
        def to_dict(self) -> dict:
            return {
                "type": "video",
                "video_url": self.video_url,
                "description": self.description
            }

    class TextSnippet(ContentSnippet):
        def __init__(self, text: str):
            self.text: str = text
        @property
        def raw_text(self) -> str:
            return self.text
        def to_dict(self) -> dict:
            return {"type": "text", "text": self.text}

    class LinkSnippet(ContentSnippet):
        def __init__(self, link: str, showtext : Optional[str] = None):
            self.link: str = link
            self.showtext : Optional[str] = showtext
        @property
        def raw_text(self) -> str:
            return self.link
        def to_dict(self) -> dict:
            return {"type": "link", "link": self.link, "showtext": self.showtext}

    def __init__(self, snippet_list: Optional[list[ContentSnippet]] = None):
        self._snippet_list: list[PageContent.ContentSnippet] = snippet_list or list()
        self._unique_links: set[URL] = \
            set() if snippet_list is None else set(map(
                lambda x: URL(x.link), # type: ignore
                filter(lambda x: isinstance(x, PageContent.LinkSnippet), snippet_list)
            )) # type: ignore

    def add_snippet(self, snippet: ContentSnippet):
        if isinstance(snippet, PageContent.LinkSnippet):
            self._unique_links.add(URL(snippet.link))
        self._snippet_list.append(snippet)
    
    def get_page_snippets(self):
        for s in self._snippet_list:
            yield s
        
    def get_media_snippets(self):
        for s in self.get_page_snippets():
            if isinstance(s, PageContent.ImageSnippet | PageContent.VideoSnippet):
                yield s

    # def get_pending_downloads(self)

    def get_text_snippets(self):
        for s in self.get_page_snippets():
            if isinstance(s, PageContent.TextSnippet):
                yield s

    def to_dict(self) -> dict:
        return {
            "snippets": [s.to_dict() for s in self._snippet_list]
        }

    @staticmethod
    def from_dict(data: dict) -> 'PageContent':
        snippet_list = [PageContent.ContentSnippet.from_dict(item) for item in data["snippets"]]
        return PageContent(snippet_list=snippet_list)
    
class WebPage:
    def __init__(self, url: URL, page_title: str, content: PageContent):
        self.url: URL = url
        self.page_title: str = page_title
        self.content: PageContent = content

    def __eq__(self, value: object) -> bool:
        if isinstance(value, WebPage):
            return self.url == value.url
        return False
    
    def __hash__(self) -> int:
        return hash("webpage : " + str(self.url))
    
    def __str__(self) -> str:
        return f"{self.page_title} : {self.url}"

    @property
    def page_unique_urls(self) -> set[URL]:
        if self.url in self.content._unique_links:
            self.content._unique_links.remove(self.url)
        return self.content._unique_links

    @property
    def page_type(self) -> str:
        return "unknown"
    
    def __hash__(self) -> int:
        return hash(self.url) - 5

    def to_dict(self) -> dict:
        data = {
            "url": str(self.url),
            "page_title": self.page_title,
            "content": self.content.to_dict(),
            "page_type": self.page_type,
        }
        return data
    
    @staticmethod
    def from_dict(data: dict) -> 'WebPage':
        url = URL(data["url"])
        page_title = data["page_title"]
        content = PageContent.from_dict(data["content"])
        page_type = data.get("page_type", "article")

        if page_type == "product":
            price_text = data.get("price")
            price_snippet = PageContent.TextSnippet(price_text) if price_text else None
            return ProductPage(url, page_title, content, price_snippet)

        elif page_type == "gallery":
            return GalleryPage(url, page_title, content)

        elif page_type == "article":
            author_text = data.get("author")
            author_snippet = PageContent.TextSnippet(author_text) if author_text else None
            return ArticlePage(url, page_title, content, author_snippet)
        
        else:
            return WebPage(url, page_title, content)

class ArticlePage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent, author_snippet: Optional[PageContent.ContentSnippet] = None):
        super().__init__(url, page_title, content)

        if author_snippet is None:
            for s in content.get_page_snippets():
                if "author" in s.raw_text:
                    author_snippet = s
        self.author_snippet = author_snippet

    @property
    def page_type(self) -> str:
        return "article"
    
    def to_dict(self) -> dict:
        data = super().to_dict()
        data["author"] = self.author_snippet.raw_text if self.author_snippet else None
        return data

class ProductPage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent, price_snippet: Optional[PageContent.TextSnippet] = None):
        super().__init__(url, page_title, content)
        if price_snippet is None:
            for t in content.get_text_snippets():
                if "price" in t.text.lower():
                    price_snippet = t
        self.price_snippet = price_snippet

    @property
    def page_type(self) -> str:
        return "product"
    
    def to_dict(self) -> dict:
        data = super().to_dict()
        data["price"] = self.price_snippet.text if self.price_snippet else None
        return data


class GalleryPage(WebPage):

    def __init__(self, url: URL, page_title: str, content: PageContent):
        super().__init__(url, page_title, content)

    @property
    def media_snippets(self):
        return self.content.get_media_snippets()
    
    @property
    def page_type(self) -> str:
        return "gallery"

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