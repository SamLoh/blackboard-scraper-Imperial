from typing import Optional
from urllib.parse import urljoin, urlsplit


BLACKBOARD_BASE_URL = "https://bb.imperial.ac.uk/"


def resolve_blackboard_url(href: str) -> Optional[str]:
    """Resolve a link against Imperial Blackboard and validate its origin."""
    try:
        url = urljoin(BLACKBOARD_BASE_URL, href)
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname != "bb.imperial.ac.uk"
            or parts.port not in (None, 443)
            or parts.username is not None
            or parts.password is not None
        ):
            return None
    except ValueError:
        return None

    return url
