from typing import Optional

from source.page import WebPage
from source.url_utils import URL

class SitemapGraph():
    def __init__(self):
        self.links : dict[URL, set[URL]] = dict()
        self._all_urls : set[URL] = set()
        self.scores : Optional[dict[URL, float]] = None

    def add_edges(self, from_url: URL, to_urls: set[URL]):
        self._all_urls.add(from_url)
        self._all_urls.update(to_urls)
        self.links[from_url] = to_urls

    def add_edge(self, from_url: URL, to_url: URL):
        if from_url == to_url:
            return
        
        if from_url not in self.links:
            self.links[from_url] = set()

        self._all_urls.update({from_url, to_url})
        self.links[from_url].add(to_url)

    def calculate_ranks(self, iterations: int = 10, damping_factor: float = 0.85):
        self.scores = dict.fromkeys(self._all_urls, 1.0 / len(self._all_urls))

        if len(self._all_urls) == 0:
            return []
        
        for _ in range(iterations):
            new_scores = dict.fromkeys(self._all_urls, (1 - damping_factor) / len(self._all_urls))
            for from_url, to_urls in self.links.items():
                each_link_weight = self.scores[from_url] / len(to_urls)
                for t in to_urls:
                    new_scores[t] += each_link_weight * damping_factor

            self.scores = new_scores

    def sort_urls_by_rank(self) -> list[URL]:
        if self.scores is None:
            raise Exception("the ranks are not calculated")
        else:
            return sorted(self._all_urls, key=lambda x: self.scores[x], reverse=True) # type: ignore

    @staticmethod
    def from_webpages(all_pages: set[WebPage], calulate_ranks : bool = True) -> 'SitemapGraph':
        graph = SitemapGraph()
        for p in all_pages:
            for link in p.page_unique_urls:
                graph.add_edges(p.url, p.page_unique_urls)

        if calulate_ranks == True:
            graph.calculate_ranks()

        return graph