from typing import Optional
from urllib.error import URLError
from urllib.robotparser import RobotFileParser
from urllib.request import Request, urlopen
from fake_useragent import UserAgent
from source.config import AppConfig
from source.url_utils import URL


class SecurityLayer:
    def __init__(self, config: AppConfig):
        self.config: AppConfig = config
        self.start_url: URL = URL(config.start_url)
        self.robot_parser: Optional[RobotFileParser] = None
        self.user_agent: UserAgent = UserAgent()
        self._init_robot_parser()

    def _to_url(self, url: str | URL) -> URL:
        return URL(url) if not isinstance(url, URL) else url

    def _init_robot_parser(self) -> None:
        if not self.start_url.is_valid:
            print("[Security] Invalid start URL.")
            return

        robots_url = URL(
            f"{self.start_url.scheme}://{self.start_url.domain}/robots.txt"
        )

        try:
            request = Request(
                url=robots_url.value,
                headers={
                    "User-Agent": self.user_agent.random
                }
            )

            self.robot_parser = RobotFileParser()

            with urlopen(request, timeout=self.config.timeout) as response:
                self.robot_parser.parse(
                    line.decode(
                        "utf-8",
                        errors="ignore"
                    )
                    for line in response.readlines()
                )

        except URLError:
            print("[Security] Could not download robots.txt")
            self.robot_parser = None

        except Exception as e:
            print(f"[Security] Unexpected error: {e}")
            self.robot_parser = None

    def _is_same_domain(self, url: str | URL) -> bool:
        url = self._to_url(url)

        return (
            url.is_valid
            and url.domain == self.start_url.domain
        )

    def _is_allowed_by_robots(self, url: str | URL) -> bool:
        url = self._to_url(url)

        if self.robot_parser is None:
            return True

        return self.robot_parser.can_fetch(
            "*",
            url.value
        )

    def should_crawl(
        self,
        url: str | URL,
        visited_urls: Optional[set[URL]] = None
    ) -> bool:
        url = self._to_url(url)

        if visited_urls is None:
            visited_urls = set()

        return (
            url.is_valid
            and self._is_same_domain(url)
            and self._is_allowed_by_robots(url)
            and url not in visited_urls
        )