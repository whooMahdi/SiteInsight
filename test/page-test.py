from source.page import PageContent, WebPage, PageFactory, GalleryPage, ProductPage, ArticlePage
from source.url_utils import URL
import json

p_content = PageContent()
p_content.add_snippet(PageContent.TextSnippet("Page 1"))
p_content.add_snippet(PageContent.TextSnippet("product 2"))
p_content.add_snippet(PageContent.ImageSnippet("https://example.com/image-2.jpg", "images/img2.jpg"))
p_content.add_snippet(PageContent.LinkSnippet("https://example.com/link-1"))
p_content.add_snippet(PageContent.LinkSnippet("https://example.com/link-2", showtext="Link to relative products"))
p_content.add_snippet(PageContent.VideoSnippet("https://example.com/video-1", description="Video 1"))
p_content.add_snippet(PageContent.TextSnippet("Price : 100 $"))

p_page = PageFactory.create_page(URL("example.com"), "title", p_content)

if isinstance(p_page, ProductPage):
    s = p_page.price_snippet
    if s is None:
        s = ""
    else:
        s = s.raw_text
    print(s)

print()
print(repr(p_page.to_dict()))
jstr = json.dumps(p_page.to_dict(), indent=4, ensure_ascii=False)
print(jstr)

# p_page_recovered = WebPage.from_dict(json.loads(jstr))
# print(p_page_recovered.content.page_links_list)
# if isinstance(p_page_recovered, ProductPage):
#     s = p_page_recovered.price_snippet
#     if s is None:
#         s = ""
#     else:
#         s = s.raw_text
#     print(s)
# print(json.dumps(p_page_recovered.to_dict(), indent=4, ensure_ascii=False))

a_content = PageContent()
a_content.add_snippet(PageContent.TextSnippet("Article 2"))
a_content.add_snippet(PageContent.TextSnippet("an article about saving images in python"))
a_content.add_snippet(PageContent.ImageSnippet("https://example.com/wide-view.jpg", "images/wide-view.jpg", "IDE Wide View"))
a_content.add_snippet(PageContent.TextSnippet("For saving images in python we need to know how to handle files and write in them"))

a_page = PageFactory.create_page(URL("https://example.com/how-to-save-images-python"), "Saving images with Python", a_content)

print()
print(a_page.page_type)

# poetry run python -m test.page-test
# prints :: Price : 100 $