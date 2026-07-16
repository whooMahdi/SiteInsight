from typing import Optional
from urllib.robotparser import RobotFileParser
import requests
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
            ua = self.user_agent.random
            headers = {"User-Agent": ua}
            
            response = requests.get(
                robots_url.value,
                headers=headers,
                timeout=self.config.timeout if hasattr(self.config, "timeout") else 5
            )

            if response.status_code == 200:
                self.robot_parser = RobotFileParser()
                # Feed the lines to robot parser safely
                self.robot_parser.parse(response.text.splitlines())
                print("[Security] Successfully loaded robots.txt via requests.")
            else:
                print(f"[Security] robots.txt returned status code: {response.status_code}. Bypassing.")
                self.robot_parser = None

        except requests.exceptions.RequestException as e:
            print(f"[Security] Could not retrieve robots.txt (Network Error/Timeout): {e}. Bypassing safety check.")
            self.robot_parser = None
        except Exception as e:
            print(f"[Security] Unexpected error loading robots.txt: {e}. Bypassing.")
            self.robot_parser = None

    def _is_same_domain(self, url: str | URL) -> bool:
        url = self._to_url(url)
        
        # Strip 'www.' from domains if present to prevent false negative domain matches
        start_domain = self.start_url.domain.lower().replace("www.", "")
        target_domain = url.domain.lower().replace("www.", "")

        return (
            url.is_valid
            and target_domain == start_domain
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