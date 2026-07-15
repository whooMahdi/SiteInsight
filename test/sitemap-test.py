from source.sitemap import SitemapGraph
from source.url_utils import URL

# A -> B, C
# B -> A
# C -> A, B

g = SitemapGraph()

A = URL('http://example.com/_A')
B = URL('http://example.com/_B')
C = URL('http://example.com/_C')

g.add_edge(A, B)
g.add_edge(A, C)
g.add_edge(B, A)
g.add_edge(C, A)
g.add_edge(C, B)

g.calculate_ranks()
result = g.sort_urls_by_rank()

scores = (g.scores or dict())
print("sort :", [str(url) for url in result])
print("scores :", {str(k): v for k, v in scores.items()})

total = sum(scores.values())
print(f"summition: {total:.6f}")

# poetry run python -m test.sitemap-test
