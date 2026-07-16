from source.url_utils import URL
from source.parser import HTMLParser
from fake_useragent import UserAgent
import json
import requests

url = URL("https://en.wikipedia.org/wiki/Parrot")

try:
    response = requests.get(url.value, timeout=10,
        headers={"User-Agent": UserAgent().random}
    )
    
    page_obj = HTMLParser.parse(response.text, url)
    
    print(f"page obj: {page_obj.page_type}")
    print(f"title: {page_obj.page_title}")
    print("\n--- (JSON) ---")
    with open("test-page.json", mode="w") as f:
        f.write(json.dumps(page_obj.to_dict(), indent=4, ensure_ascii=False))
    print("test-page.json saved")
    
except Exception as e:
    print(f"error {e}")