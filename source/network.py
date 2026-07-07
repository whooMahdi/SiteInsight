from typing import Optional, Iterable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import urllib.request
from source.config import AppConfig
from fake_useragent import UserAgent


class SecurityLayer:
    def __init__(
            self,
            config: AppConfig
        ):
        self.conf: AppConfig = config
        self.start_url: str = config.start_url
        self.parent_domain: str = self._get_clean_domain(self.start_url)
        self.robot_parser: Optional[RobotFileParser] = None
        self._init_robot_parser()

    def _get_clean_domain(self, url: str) -> str:
        try:
            domain = urlparse(url).netloc
            return domain[4:] if domain.startswith("www.") else domain
        except Exception:
            return ""
    
    def _init_robot_parser(self) -> None:
        try:
            parsed_start_url = urlparse(self.start_url)
            robots_url = f"{parsed_start_url.scheme}://{parsed_start_url.netloc}/robots.txt"

            user_agent = UserAgent()

            self.robot_parser = RobotFileParser()

            req = urllib.request.Request(
                url=robots_url,
                headers={
                    "User-Agent": user_agent.random
                }
            )

            with urllib.request.urlopen(req, timeout=5) as repsonse:
                self.robot_parser.parse(
                    line.decode("utf-8") for line in repsonse.readlines()
                )

            # print(f"[Security] robots.txt loaded successfully.")
        except Exception as e:
            print(f"[Security] Warning: Could not read robots.txt: {e}")
            self.robot_parser = None

    def _is_valid_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = urlparse(url.strip())
            return bool((parsed.scheme in ("https", "http")) and parsed.netloc)
        except Exception:
            return False

    def _is_allowed_by_robots(self, url: str, user_agent: str = "*") -> bool:
        if self.robot_parser is None:
            return True

        if self._is_same_domain(url):
            return self.robot_parser.can_fetch(user_agent, url)
        return False
    
    def _is_same_domain(self, url: str) -> bool:
        return self._get_clean_domain(url) == self.parent_domain

    def should_crawl(self, url: str, visited_urls: Iterable[str] = []) -> bool:
        return (
            self._is_valid_url(url) and
            self._is_allowed_by_robots(url) and
            url not in visited_urls
        )
