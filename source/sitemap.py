from typing import Optional

from source.page import WebPage
from source.url_utils import URL

class SitemapGraph():
    def __init__(self):
        self.edges : dict[WebPage, set[WebPage]] = dict()
        self._all_pages : dict[URL, WebPage] = dict()
        self.scores : dict[WebPage, float] = dict()

    def add_edges(self, from_page: WebPage, to_pages: set[WebPage]):
        self._all_pages[from_page.url] = from_page
        self._all_pages.update(map(lambda x: (x.url, x), to_pages))
        if from_page not in self.edges:
            self.edges[from_page] = set()
        self.edges[from_page].update(to_pages)

    def add_edge(self, from_url: WebPage, to_url: WebPage):
        if from_url == to_url:
            return
        
        if from_url not in self.edges:
            self.edges[from_url] = set()

        self._all_pages[from_url.url] = from_url
        self._all_pages[to_url.url] = to_url
        self.edges[from_url].add(to_url)

    def calculate_ranks(self, iterations: int = 10, damping_factor: float = 0.85):    
        pages_count = len(self._all_pages)    
        if pages_count == 0:
            self.scores = {}
            return
        
        all_pages_set = set(self._all_pages.values())

        self.scores = dict.fromkeys(all_pages_set, 1.0 / pages_count)
        
        for _ in range(iterations):
            new_scores = dict.fromkeys(all_pages_set, (1 - damping_factor) / pages_count)
            for from_url, to_urls in self.edges.items():
                if len(to_urls) == 0:
                    continue
                each_link_weight = self.scores[from_url] / len(to_urls)
                for t in to_urls:
                    new_scores[t] += each_link_weight * damping_factor

            

            # pages without out link

            pages_without_out = all_pages_set - set(self.edges.keys())
            if pages_without_out:
                total_score_without_out = sum(self.scores[p] for p in pages_without_out)
                each_weight = (damping_factor * total_score_without_out) / pages_count
                for page in all_pages_set:
                    new_scores[page] += each_weight


            self.scores = new_scores

    def sort_pages_by_rank(self) -> list[WebPage]:
        if len(self.scores) == 0 and len(self._all_pages) != 0:
            raise Exception("the ranks are not calculated")
        else:
            return sorted(self._all_pages.values(), key=lambda x: self.scores[x], reverse=True) # type: ignore

    @staticmethod
    def from_webpages(all_pages: set[WebPage], calulate_ranks : bool = True) -> 'SitemapGraph':
        all_pages_dict = dict(map(lambda x: (x.url, x), all_pages))
        graph = SitemapGraph()
        for p in all_pages:
            for link in p.page_unique_urls:
                if link in all_pages_dict:
                    graph.add_edge(p, all_pages_dict[link])

        if calulate_ranks:
            graph.calculate_ranks()

        return graph