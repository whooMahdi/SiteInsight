from source.page import PageContent, WebPage, PageFactory, GalleryPage, ProductPage, ArticlePage
from source.url_utils import URL

content = PageContent()
content.add_snippet(PageContent.TextSnippet("Page 1"))
content.add_snippet(PageContent.TextSnippet("product 2"))
content.add_snippet(PageContent.ImageSnippet("https://example.com/image-2.jpg"))
content.add_snippet(PageContent.LinkSnippet("https://example.com/link-1"))
content.add_snippet(PageContent.VideoSnippet("https://example.com/video-1", description="Video 1"))
content.add_snippet(PageContent.TextSnippet("Price : 100 $"))

page = PageFactory.create_page(URL("example.com"), "title", content);

if isinstance(page, ProductPage):
    s = page.price_snippet
    if s is None:
        s = ""
    else:
        s = s.raw_text
    print(s)

# poetry run python -m test.page-test
# prints :: Price : 100 $