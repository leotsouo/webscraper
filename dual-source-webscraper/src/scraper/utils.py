from urllib import robotparser
from urllib.parse import urlparse
import time, random

def allowed_by_robots(url: str, user_agent: str = "Mozilla/5.0") -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        # If robots.txt not reachable, be conservative and allow (common practice varies; adjust per policy)
        return True

def polite_delay(base: float = 0.5, jitter: float = 0.5):
    time.sleep(base + random.random()*jitter)
