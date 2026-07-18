import os
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.validation import Integer
from textual.widgets import Button, DirectoryTree, Input, Label

from source import AppConfig
from source.ui.theme import BORDER, PRIMARY, SURFACE, TEXT_MUTED


class SettingsScreen(ModalScreen[None]):
    DEFAULT_CSS = f"""
    SettingsScreen {{
        align: center middle;
    }}
    #settings_box {{
        width: 54;
        height: auto;
        padding: 1 2;
        border: heavy {PRIMARY};
        background: {SURFACE};
    }}
    #settings_box Input {{
        margin-bottom: 1;
    }}
    #settings_buttons {{
        height: auto;
        align: right middle;
        margin-top: 1;
    }}
    #settings_buttons Button {{
        margin-left: 1;
    }}
    """

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        with Vertical(id="settings_box"):
            yield Label("Max depth")
            yield Input(value=str(self.config.max_depth), id="depth_input", validators=[Integer()])
            yield Label("Max links per page")
            yield Input(value=str(self.config.max_links_per_page), id="max_links_input", validators=[Integer()])
            yield Label("Fetcher threads")
            yield Input(value=str(self.config.threads_count), id="threads_input", validators=[Integer()])
            yield Label("Image threads")
            yield Input(value=str(self.config.image_threads_count), id="image_threads_input", validators=[Integer()])
            yield Label("Timeout (seconds)")
            yield Input(value=str(self.config.timeout), id="timeout_input", validators=[Integer()])
            yield Label("Proxy URL (optional)")
            yield Input(value=self.config.proxy_url or "", id="proxy_input")
            with Horizontal(id="settings_buttons"):
                yield Button("Save", id="save_btn", variant="success")
                yield Button("Close", id="close_btn")

    def on_mount(self) -> None:
        self.query_one("#settings_box").border_title = "⚙ Settings"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            self._apply_values()
            self.config.save_to_file()
        self.dismiss()

    def _apply_values(self) -> None:
        def as_int(widget_id: str, current: int) -> int:
            value = self.query_one(f"#{widget_id}", Input).value
            return int(value) if value.isdigit() else current

        self.config.max_depth = as_int("depth_input", self.config.max_depth)
        self.config.max_links_per_page = as_int("max_links_input", self.config.max_links_per_page)
        self.config.threads_count = as_int("threads_input", self.config.threads_count)
        self.config.image_threads_count = as_int("image_threads_input", self.config.image_threads_count)
        self.config.timeout = as_int("timeout_input", self.config.timeout)

        proxy_value = self.query_one("#proxy_input", Input).value
        self.config.proxy_url = proxy_value or None


class DirectoryPickerScreen(ModalScreen[Optional[str]]):
    DEFAULT_CSS = f"""
    DirectoryPickerScreen {{
        align: center middle;
    }}
    #picker_box {{
        width: 72;
        height: 32;
        border: heavy {PRIMARY};
        background: {SURFACE};
        padding: 1 2;
    }}
    #picker_current {{
        height: 1;
        color: {TEXT_MUTED};
        margin-bottom: 1;
    }}
    #picker_box DirectoryTree {{
        height: 1fr;
        border: round {BORDER};
        margin-bottom: 1;
    }}
    #picker_buttons {{
        height: auto;
        align: right middle;
    }}
    #picker_buttons Button {{
        margin-left: 1;
    }}
    """

    def __init__(self, start_path: str):
        super().__init__()
        self._start_path = start_path if os.path.isdir(start_path) else "."
        self._selected: str = str(Path(self._start_path).resolve())

    def compose(self) -> ComposeResult:
        with Vertical(id="picker_box"):
            yield Label(f"Selected: {self._selected}", id="picker_current")
            yield DirectoryTree(self._start_path, id="picker_tree")
            with Horizontal(id="picker_buttons"):
                yield Button("Use this folder", id="pick_here_btn", variant="success")
                yield Button("Cancel", id="pick_cancel_btn")

    def on_mount(self) -> None:
        self.query_one("#picker_box").border_title = "Choose a folder"

    def on_tree_node_highlighted(self, event) -> None:
        node_data = getattr(event.node, "data", None)
        path = getattr(node_data, "path", None)
        if path is not None and os.path.isdir(path):
            self._selected = str(path)
            self.query_one("#picker_current", Label).update(f"Selected: {self._selected}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pick_here_btn":
            self.dismiss(self._selected)
        elif event.button.id == "pick_cancel_btn":
            self.dismiss(None)
