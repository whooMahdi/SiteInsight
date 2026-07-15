from typing import Optional

from anytree import Node, RenderTree
from source.page import WebPage
from source.url_utils import URL

class SitemapGraph():
    def __init__(self):
        self._edges : dict[WebPage, set[WebPage]] = dict()
        self._all_pages : dict[URL, WebPage] = dict()
        self._scores : Optional[dict[WebPage, float]] = None

    @property
    def edges(self):
        return self._edges.copy()
    
    @property
    def scores(self) -> dict[WebPage, float] | None:
        if self._scores:
            return self._scores.copy()
        else:
            return None

    def add_edges(self, from_page: WebPage, to_pages: set[WebPage]):
        self._all_pages[from_page.url] = from_page
        self._all_pages.update(map(lambda x: (x.url, x), to_pages))
        if from_page not in self._edges:
            self._edges[from_page] = set()
        self._edges[from_page].update(to_pages)

    def add_edge(self, from_url: WebPage, to_url: WebPage):
        if from_url == to_url:
            return
        
        if from_url not in self._edges:
            self._edges[from_url] = set()

        self._all_pages[from_url.url] = from_url
        self._all_pages[to_url.url] = to_url
        self._edges[from_url].add(to_url)

    def calculate_ranks(self, iterations: int = 10, damping_factor: float = 0.85):    
        pages_count = len(self._all_pages)    
        if pages_count == 0:
            return
        
        all_pages_set = set(self._all_pages.values())

        self._scores = dict.fromkeys(all_pages_set, 1.0 / pages_count)
        
        for _ in range(iterations):
            new_scores = dict.fromkeys(all_pages_set, (1 - damping_factor) / pages_count)
            for from_url, to_urls in self._edges.items():
                if len(to_urls) == 0:
                    continue
                each_link_weight = self._scores[from_url] / len(to_urls)
                for t in to_urls:
                    new_scores[t] += each_link_weight * damping_factor

            

            # pages without out link

            pages_without_out = all_pages_set - set(self._edges.keys())
            if pages_without_out:
                total_score_without_out = sum(self._scores[p] for p in pages_without_out)
                each_weight = (damping_factor * total_score_without_out) / pages_count
                for page in all_pages_set:
                    new_scores[page] += each_weight


            self._scores = new_scores

    def sort_pages_by_rank(self) -> list[WebPage]:
        if self._scores is not None:
            return sorted(self._all_pages.values(), key=lambda x: self._scores[x], reverse=True) # type: ignore
        else:
            raise Exception("the ranks are not calculated")

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
    
    def make_sitemap_text_tree(self, root_page: WebPage, max_depth: int = 8, max_children: int = 8) -> str:

        root = (Node(root_page.page_title), root_page) # node, page

        def create_sub_nodes(current_root: tuple[Node, WebPage], current_page_path: Optional[list[WebPage]] = None):
            if current_page_path is None:
                current_page_path = [current_root[1]]
            if current_root[1] not in self._edges:
                return
            if len(current_page_path) > max_depth:
                Node("...", current_root[0])
                return
            sub_pages = list(self._edges[current_root[1]])
            if self._scores:
                sub_pages.sort(key=lambda x: self._scores.get(x, 0), reverse=True) # type: ignore

            sub_pages_cutted = len(sub_pages) > max_children
            cutted_items = 0
            if sub_pages_cutted:
                cutted_items = len(sub_pages) - max_children
                sub_pages = sub_pages[:max_children]

            for page in sub_pages:
                if page not in current_page_path:
                    item = (Node(page.page_title, current_root[0]), page)
                    current_page_path.append(page)
                    create_sub_nodes(item, current_page_path)
                    current_page_path.pop()

            if sub_pages_cutted:
                Node(f"And more {cutted_items} pages ...", current_root[0])

        create_sub_nodes(root)

        return RenderTree(root[0]).by_attr()
