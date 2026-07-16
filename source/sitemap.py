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

    def add_edge(self, from_page: WebPage, to_page: WebPage):
        if from_page == to_page:
            return
        
        if from_page not in self._edges:
            self._edges[from_page] = set()

        self._all_pages[from_page.url] = from_page
        self._all_pages[to_page.url] = to_page
        self._edges[from_page].add(to_page)

    def calculate_ranks(self, iterations: int = 10, damping_factor: float = 0.85):    
        pages_count = len(self._all_pages)    
        if pages_count == 0:
            return
        
        all_pages_set = set(self._all_pages.values())

        self._scores = dict.fromkeys(all_pages_set, 1.0 / pages_count)
        
        for _ in range(iterations):
            new_scores = dict.fromkeys(all_pages_set, (1 - damping_factor) / pages_count)
            for from_page, to_page in self._edges.items():
                if len(to_page) == 0:
                    continue
                each_link_weight = self._scores[from_page] / len(to_page)
                for t in to_page:
                    new_scores[t] += each_link_weight * damping_factor

            

            # pages without out link

            pages_without_out = filter(lambda x: x not in self._edges.keys() or len(self._edges[x]) == 0, all_pages_set)
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

            # initializing : when a page is complately isolated, it should be exist in sitemap
            graph._edges[p] = set()
            graph._all_pages[p.url] = p

            for link in p.page_unique_urls:
                if link in all_pages_dict:
                    graph.add_edge(p, all_pages_dict[link])

        if calulate_ranks:
            graph.calculate_ranks()

        return graph
    
    def make_sitemap_text_tree(self, root_page: WebPage, max_depth: int = 8, max_children: int = 8, sort_by_rank : Optional[bool] = None) -> str:

        if sort_by_rank and (not self._scores):
            raise Exception("make_sitemap_text_tree : Cannot be forced to sort_by_rank because the ranks are not calculated")

        placeholder = Node("")
        root = (Node(root_page.page_title, placeholder), root_page) # node, page

        # if root is isolated show it in a better way with the placeholder
        if len(self._edges[root_page]) == 0:
            return RenderTree(placeholder).by_attr()

        def create_sub_nodes(current_root: tuple[Node, WebPage], current_page_path: Optional[list[WebPage]] = None):
            if current_page_path is None:
                current_page_path = [current_root[1]]
            if current_root[1] not in self._edges:
                return
            if len(current_page_path) > max_depth:
                Node("...", current_root[0])
                return
            sub_pages = list(self._edges[current_root[1]])
            if self._scores and not (sort_by_rank == False):
                sub_pages.sort(key=lambda x: (-self._scores.get(x, 0), len(self._edges[x]))) # type: ignore

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

    def to_text(self, sort_by_rank : Optional[bool] = None):
        if sort_by_rank and (not self._scores):
            raise Exception("get_all_edges_as_text : Cannot be forced to sort_by_rank because the ranks are not calculated")
        
        is_ranked = self.scores != None and not (sort_by_rank == False)
        if is_ranked:
            pages = self.sort_pages_by_rank()
        else:
            pages = list(self._all_pages.values())

        lines = [
            "   RANK   ||  PAGE NAME   ||   LINKED TO PAGES",
            "----------------------------------------------"
        ]
        for p in pages:
            prefix = f"  {self._scores[p]:.3f}   ::  " if is_ranked else "" # type: ignore
            line = prefix + f"{p.page_title:^10s}  ->  {[to_page.page_title for to_page in self._edges.get(p, [])]}"
            lines.append(line)
        return "\n".join(lines)
    
    def __str__(self) -> str:
        return self.to_text()