# holidays/fetcher.py
import requests
from typing import Optional

def fetch_ics(url: str, timeout: int = 15) -> Optional[str]:
    """
    下载 ICS 文件并返回文本内容。如果失败返回 None。
    """
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[fetcher] failed to fetch {url}: {e}")
        return None
