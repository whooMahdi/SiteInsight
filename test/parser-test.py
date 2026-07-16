from source.url_utils import URL
from source.parser import HTMLParser

import json
import requests

url = URL("https://roocket.ir/articles/two-factor-authentication/")

try:
    response = requests.get(url.value, timeout=10)
    
    page_obj = HTMLParser.parse(response.text, url)
    
    print(f"page obj: {page_obj.page_type}")
    print(f"title: {page_obj.page_title}")
    print("\n--- (JSON) ---")
    print(json.dumps(page_obj.to_dict(), indent=4, ensure_ascii=False))
    
except Exception as e:
    print(f"error {e}")