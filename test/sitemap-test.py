from source.sitemap import SitemapGraph
from source.url_utils import URL
from source.page import PageContent, PageFactory

# A -> B, C. D
# B -> A
# C -> A, B
# D -> nothing


content_A = PageContent()
content_A.add_snippet(PageContent.TextSnippet("Page A"))
content_A.add_snippet(PageContent.LinkSnippet("https://example.com/A", showtext="Page A"))
content_A.add_snippet(PageContent.LinkSnippet("https://example.com/B", showtext="Page B"))
content_A.add_snippet(PageContent.LinkSnippet("https://example.com/C", showtext="Page C"))
content_A.add_snippet(PageContent.LinkSnippet("https://example.com/D", showtext="Page C"))

page_A = PageFactory.create_page(URL("https://example.com/A"), "A", content_A)

content_B = PageContent()
content_B.add_snippet(PageContent.TextSnippet("Page B"))
content_B.add_snippet(PageContent.LinkSnippet("https://example.com/link-2", showtext="Link to relative products"))
content_B.add_snippet(PageContent.LinkSnippet("https://example.com/A", showtext="Page A"))

page_B = PageFactory.create_page(URL("https://example.com/B"), "B", content_B)

content_C = PageContent()
content_C.add_snippet(PageContent.TextSnippet("Page C"))
content_C.add_snippet(PageContent.LinkSnippet("https://example.com/A", showtext="Page A"))
content_C.add_snippet(PageContent.LinkSnippet("https://example.com/B", showtext="Page B"))

page_C = PageFactory.create_page(URL("https://example.com/C"), "C", content_C)

page_D = PageFactory.create_page(URL("https://example.com/D"), "D", PageContent())


# ------------------------------------------------------------------------
# A -> B, C. D
# B -> A
# C -> A, B
# D -> nothing

all_pages = {page_A, page_B, page_C, page_D}

graph = SitemapGraph.from_webpages(all_pages)

scores = (graph.scores or dict())
print("sort :", [str(page) for page in graph.sort_pages_by_rank()])
print("scores :", {str(k): v for k, v in scores.items()})

total = sum(scores.values())
print(f"sum: {total:.6f}")

print(graph.make_sitemap_text_tree(page_A))
print(graph.to_text())

# poetry run python -m test.sitemap-test
