import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.validation import Integer
from textual.widgets import (
    Button,
    ContentSwitcher,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    ProgressBar,
    RichLog,
    Sparkline,
    Static,
)
from textual.widgets.option_list import Option

from source import AppConfig, Crawler
from source.utils import shortner


MIN_WIDTH = 104
MIN_HEIGHT = 32

BG = "#120f0c"
SURFACE = "#1a1512"
PANEL = "#211a15"
BORDER = "#3d2c1c"
PRIMARY = "#f97316"      
SECONDARY = "#fbbf24"    
TEXT_MUTED = "#a8927e"
SUCCESS = "#22c55e"
WARNING = "#facc15"
ERROR = "#ef4444"


# helpers


def _style_log_line(line: str) -> Text:
    if "[ERROR]" in line or line.startswith("[HTTP 4") or line.startswith("[HTTP 5") or "error" in line.lower():
        style = "bold red"
    elif line.startswith("[HTTP"):
        style = "yellow"
    elif "Downloaded Image" in line:
        style = "bold green"
    elif "Failed to download image" in line:
        style = "red"
    elif "[+] Added to Queue" in line:
        style = "bright_cyan"
    elif "[-] Skipped" in line:
        style = "grey58"
    elif line.startswith("[~]") or line.startswith("FINAL REPORT") or line.startswith('"'):
        style = "bold magenta"
    else:
        style = "white"

    text = Text(f"{time.strftime('%H:%M:%S')}  ", style="dim")
    text.append(line, style=style)
    return text


def _open_in_file_manager(path: str) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform.startswith("win"):
            subprocess.Popen(["explorer", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


# modals


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
        self.query_one("#picker_box").border_title = "Choose output directory"

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


# main app


class CrawlerApp(App):
    TITLE = "SiteInsight"
    ENABLE_COMMAND_PALETTE = False

    CSS = f"""
    Screen {{
        background: {BG};
    }}
    #app_root {{
        width: 100%;
        height: 1fr;
        border: heavy {PRIMARY};
        padding: 1 2;
        background: {SURFACE};
    }}
    #body {{
        height: 1fr;
    }}
    #main_col {{
        width: 1fr;
        height: 100%;
        padding-right: 2;
    }}
    #url_row {{
        height: 3;
    }}
    #url_input {{
        width: 1fr;
        margin-right: 1;
    }}
    #url_row Button {{
        margin-left: 1;
    }}
    #output_row {{
        height: 3;
        margin-top: 1;
    }}
    #output_prefix {{
        width: 3;
        content-align: center middle;
        color: {SECONDARY};
        text-style: bold;
    }}
    #output_input {{
        width: 1fr;
        margin-right: 1;
    }}
    #output_suggestions {{
        margin-left: 3;
        max-height: 7;
        border: round {SECONDARY};
        background: {PANEL};
        display: none;
    }}
    #output_status {{
        height: 1;
        color: {TEXT_MUTED};
        padding-left: 3;
    }}
    #status_row {{
        height: 3;
        margin-top: 1;
    }}
    #status_dot {{
        width: 2;
        content-align: center middle;
        text-style: bold;
    }}
    .dot-idle {{ color: {TEXT_MUTED}; }}
    .dot-running {{ color: {WARNING}; }}
    .dot-done {{ color: {SUCCESS}; }}
    .dot-error {{ color: {ERROR}; }}

    #status {{
        width: 1fr;
        content-align: left middle;
        color: {TEXT_MUTED};
    }}
    #view_tabs {{
        height: 3;
        margin-top: 1;
    }}
    #view_tabs Button {{
        margin-right: 1;
    }}
    #clear_log_btn {{
        margin-left: 1;
    }}
    
    #switcher_container {{
        height: 1fr;
        border: round {BORDER};
        background: {PANEL};
    }}
    #log, #pages, #report {{
        width: 100%;
        height: 100%;
    }}
    #pages {{
        background: transparent;
        border: none;
    }}

    #sidebar {{
        width: 36;
        height: 100%;
        border: round {BORDER};
        padding: 1 2;
        background: {PANEL};
    }}
    #hero_pages {{
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: {SECONDARY};
    }}
    #hero_label {{
        height: 1;
        content-align: center middle;
        color: {TEXT_MUTED};
        margin-bottom: 1;
    }}
    .bar_block {{
        height: 3;
        margin-bottom: 1;
    }}
    .bar_block Static {{
        height: 1;
        color: {TEXT_MUTED};
    }}
    #rate_header {{
        height: 1;
        margin-top: 1;
    }}
    #sparkline_label {{
        width: 1fr;
        color: {TEXT_MUTED};
    }}
    #rate_value {{
        width: auto;
        color: {SUCCESS};
        text-style: bold;
    }}
    #pages_sparkline {{
        height: 3;
        color: {SECONDARY};
        margin-bottom: 1;
    }}
    .side-row {{
        height: 1;
        margin-bottom: 1;
    }}
    .side-label {{
        width: 1fr;
        color: {TEXT_MUTED};
    }}
    .side-value {{
        width: auto;
        text-style: bold;
    }}
    #resize_warning {{
        width: 100%;
        content-align: center middle;
        color: {WARNING};
        text-style: bold;
    }}
    """

    BINDINGS = [
        ("s", "open_settings", "Settings"),
        ("ctrl+l", "clear_log", "Clear log"),
        ("ctrl+t", "cycle_view", "Cycle Tabs"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.crawler: Optional[Crawler] = None
        self._crawl_running = False
        self._last_pages_count = 0
        self._history: list[float] = []
        self._views = ["log", "pages", "report"]
        self._active_view_idx = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="app_root"):
            with Horizontal(id="body"):
                with Vertical(id="main_col"):
                    with Horizontal(id="url_row"):
                        yield Input(
                            value=self.config.start_url or "",
                            placeholder="https://example.com",
                            id="url_input",
                        )
                        yield Button("▶ Crawl", id="crawl_btn", variant="success")
                        yield Button("⚙ Settings", id="settings_btn")

                    with Horizontal(id="output_row"):
                        yield Label(">", id="output_prefix")
                        yield Input(
                            value=self.config.output_dir,
                            placeholder="output/",
                            id="output_input",
                        )
                        yield Button("📁 Browse", id="browse_btn")
                    yield OptionList(id="output_suggestions")
                    yield Static("", id="output_status")

                    with Horizontal(id="status_row"):
                        yield Static("●", id="status_dot", classes="dot-idle")
                        yield Static("Idle", id="status")
                        yield Button("📂 Open folder", id="open_folder_btn", disabled=True)

                    with Horizontal(id="view_tabs"):
                        yield Button("🗎 Log", id="view_log_btn", variant="primary")
                        yield Button("📄 Pages", id="view_pages_btn")
                        yield Button("📊 Report", id="view_report_btn")
                        yield Button("Clear", id="clear_log_btn")

                    with ContentSwitcher(id="switcher_container", initial="log"):
                        yield RichLog(id="log", highlight=False, markup=False)
                        yield DataTable(id="pages")
                        yield RichLog(id="report", highlight=False, markup=True)

                with Vertical(id="sidebar"):
                    yield Static("0", id="hero_pages")
                    yield Static("pages crawled", id="hero_label")

                    with Vertical(classes="bar_block"):
                        yield Static("Fetch threads", id="fetch_bar_label")
                        yield ProgressBar(id="fetch_bar", show_eta=False)
                    with Vertical(classes="bar_block"):
                        yield Static("Image threads", id="image_bar_label")
                        yield ProgressBar(id="image_bar", show_eta=False)

                    with Horizontal(id="rate_header"):
                        yield Static("Rate", id="sparkline_label")
                        yield Static("0.0/s", id="rate_value")
                    yield Sparkline([], id="pages_sparkline")

                    yield self._side_stat("Failed", "stat_failed")
                    yield self._side_stat("URL queue", "stat_urlq")
                    yield self._side_stat("Image queue", "stat_imgq")
                    yield self._side_stat("Elapsed", "stat_elapsed")
        yield Footer()
        yield Static(id="resize_warning")

    def _side_stat(self, label: str, value_id: str) -> Horizontal:
        return Horizontal(
            Label(label, classes="side-label"),
            Static("0", id=value_id, classes="side-value"),
            classes="side-row",
        )

    def on_mount(self) -> None:
        self.query_one("#sidebar").border_title = "Live Stats"

        self.query_one("#fetch_bar", ProgressBar).total = self.config.threads_count
        self.query_one("#image_bar", ProgressBar).total = self.config.image_threads_count
        self.query_one("#output_suggestions", OptionList).display = False

        table = self.query_one("#pages", DataTable)
        table.add_columns("Type", "Title", "URL")
        table.cursor_type = "row"

        self._set_active_view("log")

        self.set_interval(0.5, self._refresh_stats)
        self._check_size()
        self.set_focus(self.query_one("#url_input", Input))

    def on_resize(self, event) -> None:
        self._check_size()

    def _check_size(self) -> None:
        width, height = self.size
        too_small = width < MIN_WIDTH or height < MIN_HEIGHT

        self.query_one("#app_root").display = not too_small
        warning = self.query_one("#resize_warning", Static)
        warning.display = too_small
        if too_small:
            warning.update(
                f"Terminal too small ({width}x{height}).\n"
                f"Please resize to at least {MIN_WIDTH}x{MIN_HEIGHT}."
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "output_input":
            self.config.output_dir = event.value
            self._update_output_suggestions(event.value)

    def _suggest_dirs(self, partial: str) -> list[str]:
        partial = partial.strip()
        if partial == "" or partial.endswith(("/", os.sep)):
            base = Path(partial) if partial and Path(partial).is_dir() else Path(".")
            prefix = ""
        else:
            path = Path(partial)
            base = path.parent if str(path.parent) not in ("", ".") else Path(".")
            prefix = path.name

        if not base.exists() or not base.is_dir():
            return []

        try:
            matches = sorted(
                entry.name for entry in base.iterdir()
                if entry.is_dir()
                and entry.name.lower().startswith(prefix.lower())
                and not entry.name.startswith(".")
            )
        except PermissionError:
            return []

        return [str(base / name) + "/" for name in matches[:8]]

    def _update_output_suggestions(self, value: str) -> None:
        option_list = self.query_one("#output_suggestions", OptionList)
        status = self.query_one("#output_status", Static)
        option_list.clear_options()

        value = value.strip()
        if not value:
            option_list.display = False
            status.update("")
            return

        matches = self._suggest_dirs(value)
        if matches:
            for suggestion in matches:
                option_list.add_option(Option(suggestion))
            option_list.display = True
            status.update("")
        else:
            option_list.display = False
            if os.path.isdir(value):
                status.update("✓ this folder exists")
            else:
                status.update("· new folder — will be created")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id != "output_suggestions":
            return

        chosen = str(event.option.prompt)
        output_input = self.query_one("#output_input", Input)
        output_input.value = chosen
        self.config.output_dir = chosen.rstrip("/")

        event.option_list.clear_options()
        event.option_list.display = False
        self.query_one("#output_status", Static).update("✓ this folder exists")
        output_input.focus()

    def action_browse_output(self) -> None:
        current = self.query_one("#output_input", Input).value.strip() or "."
        self.push_screen(DirectoryPickerScreen(current), self._on_dir_picked)

    def _on_dir_picked(self, path: Optional[str]) -> None:
        if path is None:
            return
        output_input = self.query_one("#output_input", Input)
        output_input.value = path
        self.config.output_dir = path
        self._update_output_suggestions("")
        self.query_one("#output_status", Static).update("✓ this folder exists")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "crawl_btn":
            self.start_crawl()
        elif event.button.id == "settings_btn":
            self.action_open_settings()
        elif event.button.id == "browse_btn":
            self.action_browse_output()
        elif event.button.id == "clear_log_btn":
            self.action_clear_log()
        elif event.button.id == "view_log_btn":
            self._set_active_view("log")
        elif event.button.id == "view_pages_btn":
            self._set_active_view("pages")
        elif event.button.id == "view_report_btn":
            self._set_active_view("report")
        elif event.button.id == "open_folder_btn":
            self._open_output_folder()

    def action_open_settings(self) -> None:
        self.push_screen(SettingsScreen(self.config))

    def action_clear_log(self) -> None:
        switcher = self.query_one("#switcher_container", ContentSwitcher)
        if switcher.current == "log":
            self.query_one("#log", RichLog).clear()
        elif switcher.current == "report":
            self.query_one("#report", RichLog).clear()

    def action_cycle_view(self) -> None:
        self._active_view_idx = (self._active_view_idx + 1) % len(self._views)
        self._set_active_view(self._views[self._active_view_idx])

    def _set_active_view(self, view: str) -> None:
        self.query_one("#switcher_container", ContentSwitcher).current = view
        self._active_view_idx = self._views.index(view)
        
        self.query_one("#view_log_btn", Button).variant = "primary" if view == "log" else "default"
        self.query_one("#view_pages_btn", Button).variant = "primary" if view == "pages" else "default"
        self.query_one("#view_report_btn", Button).variant = "primary" if view == "report" else "default"
        self.query_one("#clear_log_btn", Button).disabled = view == "pages"

    def _open_output_folder(self) -> None:
        path = os.path.abspath(self.config.output_dir)
        if os.path.isdir(path):
            _open_in_file_manager(path)

    def _set_state(self, state: str, text: str) -> None:
        self.query_one("#status_dot", Static).set_classes(f"dot-{state}")
        self.query_one("#status", Static).update(text)

    def start_crawl(self) -> None:
        if self._crawl_running:
            return

        url = self.query_one("#url_input", Input).value.strip()
        if not url:
            self._set_state("error", "Enter a URL first.")
            return

        self.config.start_url = url
        self._crawl_running = True
        self.crawler = None
        self._last_pages_count = 0
        self._history = []
        self.query_one("#pages_sparkline", Sparkline).data = []
        self.query_one("#pages", DataTable).clear()
        self.query_one("#report", RichLog).clear()

        for widget_id in ("crawl_btn", "settings_btn", "browse_btn"):
            self.query_one(f"#{widget_id}", Button).disabled = True
        self.query_one("#url_input", Input).disabled = True
        self.query_one("#output_input", Input).disabled = True
        self.query_one("#open_folder_btn", Button).disabled = True

        self._set_state("running", "Starting...")
        self._run_crawl()

    @work(thread=True)
    def _run_crawl(self) -> None:
        log = self.query_one("#log", RichLog)
        old_stdout = sys.stdout
        sys.stdout = _LogRedirector(self, log)

        try:
            crawler = Crawler(self.config)
            self.crawler = crawler
            self.call_from_thread(self._set_state, "running", "Crawling...")

            pages = crawler.crawl()
            result = f"Done — {len(pages)} pages crawled, {crawler.failed_pages} failed."
        except Exception as e:
            result = f"Failed: {e}"
        finally:
            sys.stdout = old_stdout
            self.call_from_thread(self._on_crawl_finished, result)

    def _on_crawl_finished(self, result: str) -> None:
        state = "error" if result.startswith("Failed") else "done"
        self._set_state(state, result)

        for widget_id in ("crawl_btn", "settings_btn", "browse_btn"):
            self.query_one(f"#{widget_id}", Button).disabled = False
        self.query_one("#url_input", Input).disabled = False
        self.query_one("#output_input", Input).disabled = False

        output_dir = os.path.abspath(self.config.output_dir)
        self.query_one("#open_folder_btn", Button).disabled = not os.path.isdir(output_dir)

        self._crawl_running = False
        
        if state == "done":
            self.notify(f"Crawl completed successfully!", title="SiteInsight", severity="information")
            self._load_report()
        else:
            self.notify(f"Crawl finished with errors.", title="SiteInsight", severity="error")

    def _load_report(self) -> None:
        report_path = Path(self.config.output_dir) / "report.txt"
        viewer = self.query_one("#report", RichLog)
        viewer.clear()
        if report_path.exists():
            try:
                content = report_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    viewer.write(Text(line, style="bright_yellow" if ":" in line else "white"))
                self._set_active_view("report")
            except Exception as e:
                viewer.write(f"[red]Error loading report: {e}[/red]")
        else:
            viewer.write("[yellow]No report.txt found in the output folder.[/yellow]")

    def _refresh_stats(self) -> None:
        crawler = self.crawler

        active_fetch = crawler.active_fetchers if crawler else 0
        active_image = crawler.active_image_workers if crawler else 0
        pages = len(crawler.pages) if crawler else 0
        failed = crawler.failed_pages if crawler else 0
        url_q = crawler.url_queue.qsize() if crawler else 0
        img_q = crawler.image_queue.qsize() if crawler else 0

        if crawler and crawler.end_time is not None:
            elapsed = crawler.end_time - crawler.start_time
        elif crawler and crawler.start_time is not None:
            elapsed = time.time() - crawler.start_time
        else:
            elapsed = 0.0

        fetch_bar = self.query_one("#fetch_bar", ProgressBar)
        fetch_bar.total = self.config.threads_count
        fetch_bar.progress = active_fetch
        self.query_one("#fetch_bar_label", Static).update(
            f"Fetch threads  {active_fetch}/{self.config.threads_count}"
        )

        image_bar = self.query_one("#image_bar", ProgressBar)
        image_bar.total = self.config.image_threads_count
        image_bar.progress = active_image
        self.query_one("#image_bar_label", Static).update(
            f"Image threads  {active_image}/{self.config.image_threads_count}"
        )

        old_count = self._last_pages_count
        delta = max(0, pages - old_count)
        self._last_pages_count = pages

        self._history.append(delta)
        if len(self._history) > 40:
            self._history.pop(0)
        self.query_one("#pages_sparkline", Sparkline).data = self._history
        self.query_one("#rate_value", Static).update(f"{delta / 0.5:.1f}/s")

        if crawler and delta:
            table = self.query_one("#pages", DataTable)
            for webpage in crawler.pages[old_count:pages]:
                table.add_row(
                    webpage.page_type,
                    shortner(webpage.page_title, head=22, tail=0, threshold=22),
                    shortner(str(webpage.url), head=26, tail=10),
                )
            if table.row_count > 300:
                for _ in range(table.row_count - 300):
                    oldest_key = next(iter(table.rows))
                    table.remove_row(oldest_key)

        self.query_one("#hero_pages", Static).update(str(pages))
        self.query_one("#stat_failed", Static).update(str(failed))
        self.query_one("#stat_urlq", Static).update(str(url_q))
        self.query_one("#stat_imgq", Static).update(str(img_q))
        self.query_one("#stat_elapsed", Static).update(f"{elapsed:.1f}s")

        option_list = self.query_one("#output_suggestions", OptionList)
        output_input = self.query_one("#output_input", Input)
        if option_list.display and self.focused not in (output_input, option_list):
            option_list.display = False


class _LogRedirector:
    def __init__(self, app: "CrawlerApp", log: RichLog):
        self.app = app
        self.log = log
        self._buffer = ""

    def write(self, text: str) -> int:
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self.app.call_from_thread(self.log.write, _style_log_line(line))
        return len(text)

    def flush(self) -> None:
        pass


def run_tui(config: Optional[AppConfig] = None) -> None:
    config = config or AppConfig.create_from_file()
    CrawlerApp(config).run()


if __name__ == "__main__":
    AppConfig.create_default_config_file()
    run_tui()