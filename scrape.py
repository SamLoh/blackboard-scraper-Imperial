import mimetypes
import re
import sys
from email.message import Message
from pathlib import Path
from urllib.parse import parse_qs, urldefrag, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

import headers as authentication
from blackboard_urls import resolve_blackboard_url
from course_links import course_links


visited_urls = set()
session = requests.Session()
session.headers.update(getattr(authentication, "headers", {}))
for cookie_name, cookie_value in getattr(authentication, "cookies", {}).items():
    session.cookies.set(cookie_name, cookie_value, domain="bb.imperial.ac.uk", path="/")


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(". ")
    if not name or re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", name.split(".")[0], re.I):
        return "_"
    return name


def save_file(response, folder, name):
    disposition = Message()
    disposition["Content-Disposition"] = response.headers.get("Content-Disposition", "")
    filename = disposition.get_filename()
    if not filename:
        filename = name
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if not Path(filename).suffix:
            filename += mimetypes.guess_extension(content_type) or ""

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / safe_name(filename)
    if destination.exists():
        print(f"Already exists: {destination}")
        return

    temporary = destination.with_name(destination.name + ".part")
    try:
        temporary.write_bytes(response.content)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Downloaded: {destination}")


def download_content(url, cur_path, ignore_course_menu=True, verbose=True, name="file"):
    url = resolve_blackboard_url(url)
    if url is None:
        return
    url = urldefrag(url)[0]
    if url in visited_urls:
        return
    visited_urls.add(url)

    response = session.get(url, timeout=30)
    response.raise_for_status()
    if resolve_blackboard_url(response.url) is None:
        raise RuntimeError("Blackboard sign-in expired. Refresh the cookies in headers.py.")

    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if content_type not in ("text/html", "application/xhtml+xml") or response.headers.get(
        "Content-Disposition", ""
    ).lower().startswith("attachment"):
        save_file(response, cur_path, name)
        return

    soup = BeautifulSoup(response.content, "html.parser")
    if soup.select_one('input[type="password"], #loginForm'):
        raise RuntimeError("Blackboard sign-in is required. Add current cookies to headers.py.")
    if verbose:
        print(f"Scanning: {cur_path}")
    content = soup.find("div", id="content") if ignore_course_menu else None
    content = content or soup

    for link in content.find_all(["a", "iframe", "frame"]):
        href = link.get("href") or link.get("src")
        if not href:
            continue
        target = resolve_blackboard_url(urljoin(response.url, href))
        if target is None:
            continue
        parts = urlsplit(target)
        allowed = (
            parts.path.startswith("/bbcswebdav/")
            or parts.path.startswith("/webapps/blackboard/content/listContent")
            or parts.path == "/webapps/blackboard/content/launchLink.jsp"
            or parts.path == "/webapps/blackboard/execute/courseMain"
            or parts.path == "/webapps/blackboard/execute/content/file"
        )
        if not allowed or "tool_id" in parse_qs(parts.query):
            continue

        title = " ".join(link.get_text(" ", strip=True).split()) or "file"
        folder = Path(cur_path)
        if parts.path.startswith("/webapps/blackboard/content/listContent"):
            folder /= safe_name(title)
        try:
            download_content(target, folder, name=title)
        except (requests.RequestException, OSError) as error:
            print(f"Failed: {title} ({error})", file=sys.stderr)


def download_file(url, path, name):
    download_content(url, path, name=name)


def main():
    if not course_links:
        print("Add the courses to download in course_links.py.", file=sys.stderr)
        return 1
    if not getattr(authentication, "cookies", {}) and not session.headers.get("Cookie"):
        print("Add your signed-in Blackboard cookies to headers.py.", file=sys.stderr)
        return 1

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "downloads"
    failed = False
    for name, url in course_links.items():
        try:
            download_content(url, output / safe_name(name), ignore_course_menu=False)
        except (requests.RequestException, OSError, RuntimeError) as error:
            print(f"Failed: {name} ({error})", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
