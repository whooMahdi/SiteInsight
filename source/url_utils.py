from urllib.parse import urlparse, urlunparse, ParseResult
from typing import Optional


class URL:
    def __init__(self, url: Optional[str], remove_trailing_slash: bool = False):
        self.remove_trailing_slash: bool = remove_trailing_slash
        self._raw_url = url.strip() if isinstance(url, str) else ""
        self._parsed = self._normalize(self._raw_url)

    def _normalize(self, url: str) -> ParseResult:
        if not isinstance(url, str):
            return urlparse("")

        url = url.strip()

        if not url: return urlparse("")

        if "://" not in url:
            url = "https://" + url

        parsed = urlparse(url)

        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            scheme = "https"

        hostname = (parsed.hostname or "").lower()
        hostname = hostname[4:] if hostname.startswith("www.") else hostname

        port = parsed.port

        if (scheme == "http" and port == 80) or \
           (scheme == "https" and port == 443):
            netloc = hostname
        elif port:
            netloc = f"{hostname}:{port}"
        else:
            netloc = hostname

        path = parsed.path
        path = "" if path == "/" else path
        if self.remove_trailing_slash and path.endswith("/"):
            path = path[:-1]

        return parsed._replace(
            scheme=scheme,
            netloc=netloc,
            path=path,
            params="",
            fragment=""
        )

    @property
    def scheme(self) -> str:
        return self._parsed.scheme

    @property
    def domain(self) -> str:
        return self._parsed.hostname or ""

    @property
    def port(self) -> Optional[int]:
        return self._parsed.port

    @property
    def path(self) -> str:
        return self._parsed.path

    @property
    def query(self) -> str:
        return self._parsed.query

    @property
    def value(self) -> str:
        return urlunparse(self._parsed)

    @property
    def is_valid(self) -> bool:
        return (
            self.scheme in ("http", "https")
            and bool(self.domain)
        )

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"URL('{self.value}')"

    def __eq__(self, other):
        return isinstance(other, URL) and self.value == other.value

    def __hash__(self):
        return hash(self.value)