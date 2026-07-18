from pathlib import Path
from typing import Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, ListItem, ListView, Static

from source.ui.archive import CATEGORY_ORDER, PageArchive, PageRef
from source.ui.dialogs import DirectoryPickerScreen
from source.page import PageContent
from source.ui.theme import BORDER, PANEL, PRIMARY, SECONDARY, SURFACE, TEXT_MUTED

try:
    from textual_image.widget import Image as TermImage
    HAS_TEXTUAL_IMAGE = True
except ImportError:
    HAS_TEXTUAL_IMAGE = False


CATEGORY_LABELS = {
    "article": "article :",
    "product": "product :",
    "gallery": "gallery :",
}


class PageBrowserScreen(Screen):
    """Read-only viewer for pages a previous crawl saved to disk."""

    DEFAULT_CSS = f"""
    PageBrowserScreen {{
        background: {SURFACE};
    }}

    #browser_root {{
        height: 1fr;
        padding: 1 2;
    }}

    #browser_toolbar {{
        height: 3;
    }}

    #browser_path {{
        width: 1fr;
        content-align: left middle;
        color: {TEXT_MUTED};
    }}

    #browser_toolbar Button {{
        margin-left: 1;
    }}

    #browser_body {{
        height: 1fr;
        margin-top: 1;
    }}

    #page_sidebar {{
        width: 36;
        height: 100%;
        border: round {BORDER};
        background: {PANEL};
        padding: 0 1;
    }}

    .category-header {{
        text-style: bold underline;
        color: {SECONDARY};
        margin-top: 1;
    }}

    #page_content {{
        width: 1fr;
        height: 100%;
        border: round {BORDER};
        background: {PANEL};
        padding: 1 2;
        margin-left: 1;
    }}

    .reader-h1 {{
        text-style: bold;
        color: {SECONDARY};
        margin-bottom: 1;
    }}

    .reader-p {{
        margin-bottom: 1;
    }}

    .reader-link {{
        color: {PRIMARY};
        margin-bottom: 1;
    }}

    .reader-caption {{
        color: {TEXT_MUTED};
        margin-bottom: 1;
    }}

    .reader-image {{
        margin-bottom: 1;
    }}
    """

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, root: str):
        super().__init__()
        self._root = Path(root)
        self._archive = PageArchive(str(self._root))
        self._groups: Dict[str, List[PageRef]] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="browser_root"):
            with Horizontal(id="browser_toolbar"):
                yield Static(str(self._root), id="browser_path")
                yield Button("Choose folder", id="change_folder_btn")
                yield Button("Close", id="close_browser_btn", variant="success")
            with Horizontal(id="browser_body"):
                yield ListView(id="page_sidebar")
                yield VerticalScroll(id="page_content")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#page_sidebar").border_title = "Pages"
        self.query_one("#page_content").border_title = "Content"
        self._load_archive()

    def _load_archive(self) -> None:
        self._groups = self._archive.scan()
        sidebar = self.query_one("#page_sidebar", ListView)
        sidebar.clear()

        content_pane = self.query_one("#page_content", VerticalScroll)
        content_pane.remove_children()

        if not self._groups:
            sidebar.append(ListItem(Label("No pages found in this folder.")))
            content_pane.mount(Label(
                "This folder doesn't have article/product/gallery subfolders "
                "with saved pages in it. Try a different output folder.",
                classes="reader-caption",
            ))
            return

        content_pane.mount(Label("Select a page on the left to read it.", classes="reader-caption"))

        for category in CATEGORY_ORDER:
            refs = self._groups.get(category)
            if not refs:
                continue

            header = ListItem(Label(CATEGORY_LABELS.get(category, category + " :"), classes="category-header"))
            header.disabled = True
            sidebar.append(header)

            for i, ref in enumerate(refs):
                sidebar.append(ListItem(Label(ref.title), id=f"page_{category}_{i}"))

    def _ref_from_item_id(self, item_id: str) -> Optional[PageRef]:
        try:
            _, category, idx = item_id.split("_", 2)
            return self._groups[category][int(idx)]
        except (ValueError, KeyError, IndexError):
            return None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if not item_id:
            return
        ref = self._ref_from_item_id(item_id)
        if ref is not None:
            self._render_page(ref)

    def _render_page(self, ref: PageRef) -> None:
        content_pane = self.query_one("#page_content", VerticalScroll)
        content_pane.remove_children()

        try:
            webpage = self._archive.load_page(ref)
        except Exception as e:
            content_pane.mount(Label(f"Could not load page: {e}", classes="reader-caption"))
            return

        content_pane.mount(Label(webpage.page_title, classes="reader-h1"))
        content_pane.mount(Label(str(webpage.url), classes="reader-caption"))

        for snippet in webpage.content.get_page_snippets():
            self._render_snippet(content_pane, ref, snippet)

    def _render_snippet(self, container: VerticalScroll, ref: PageRef, snippet) -> None:
        if isinstance(snippet, PageContent.TextSnippet):
            container.mount(Label(snippet.text, classes="reader-p"))

        elif isinstance(snippet, PageContent.LinkSnippet):
            text = snippet.showtext or snippet.link
            container.mount(Label(f"🔗 {text}", classes="reader-link"))

        elif isinstance(snippet, PageContent.ImageSnippet):
            self._render_image(container, ref, snippet)

        elif isinstance(snippet, PageContent.VideoSnippet):
            container.mount(Label(f"▶ video: {snippet.video_url}", classes="reader-link"))
            if snippet.description:
                container.mount(Label(snippet.description, classes="reader-caption"))

    def _render_image(self, container: VerticalScroll, ref: PageRef, snippet: PageContent.ImageSnippet) -> None:
        local_path = ref.folder / snippet.image_local_path if snippet.image_local_path else None

        if local_path and local_path.is_file():
            if HAS_TEXTUAL_IMAGE:
                try:
                    img = TermImage(str(local_path))
                    img.styles.width = 40
                    img.styles.height = 16
                    img.add_class("reader-image")
                    container.mount(img)
                except Exception:
                    container.mount(Label(f"🖼 {local_path.name}", classes="reader-caption"))
            else:
                container.mount(Label(f"🖼 {local_path.name} (image rendering not installed)", classes="reader-caption"))
        else:
            container.mount(Label(f"🖼 {snippet.image_url} (not downloaded)", classes="reader-caption"))

        if snippet.description:
            container.mount(Label(snippet.description, classes="reader-caption"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_browser_btn":
            self.action_go_back()
        elif event.button.id == "change_folder_btn":
            self._change_folder()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def _change_folder(self) -> None:
        self.app.push_screen(DirectoryPickerScreen(str(self._root)), self._on_new_folder)

    def _on_new_folder(self, path: Optional[str]) -> None:
        if not path:
            return
        self._root = Path(path)
        self._archive = PageArchive(str(self._root))
        self.query_one("#browser_path", Static).update(str(self._root))
        self._load_archive()
