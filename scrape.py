import mimetypes
import re
import sys
from concurrent.futures import ALL_COMPLETED, FIRST_COMPLETED, ThreadPoolExecutor, wait
from email.message import Message
from pathlib import Path
from urllib.parse import parse_qs, urldefrag, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

import headers as authentication
from blackboard_urls import resolve_blackboard_url
from course_links import course_links


MAX_DOWNLOADS = 3
visited_urls = set()
download_pool = None
pending_downloads = {}
download_errors = False
session = requests.Session()
session.headers.update(getattr(authentication, "headers", {}))
for cookie_name, cookie_value in getattr(authentication, "cookies", {}).items():
    session.cookies.set(cookie_name, cookie_value, domain="bb.imperial.ac.uk", path="/")


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(". ")
    if not name or re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", name.split(".")[0], re.I):
        return "_"
    return name


def file_destination(response, folder, name):
    disposition = Message()
    disposition["Content-Disposition"] = response.headers.get("Content-Disposition", "")
    filename = disposition.get_filename()
    if not filename:
        filename = name
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if not Path(filename).suffix:
            filename += mimetypes.guess_extension(content_type) or ""
    return Path(folder) / safe_name(filename)


def save_file(response, folder, name):
    with response:
        destination = file_destination(response, folder, name)
        if destination.exists():
            print(f"Already exists: {destination}")
            return

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".part")
        try:
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        handle.write(chunk)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Downloaded: {destination}")


def finish_downloads(wait_for_all=False):
    global download_errors
    if not pending_downloads:
        return
    completed, _ = wait(
        pending_downloads,
        return_when=ALL_COMPLETED if wait_for_all else FIRST_COMPLETED,
    )
    for future in completed:
        destination = pending_downloads.pop(future)
        try:
            future.result()
        except (requests.RequestException, OSError) as error:
            print(f"Failed: {destination} ({error})", file=sys.stderr)
            download_errors = True


def queue_download(response, folder, name):
    destination = file_destination(response, folder, name)
    if destination.exists():
        response.close()
        print(f"Already exists: {destination}")
    elif destination in pending_downloads.values():
        response.close()
        print(f"Already queued: {destination}")
    elif download_pool is None:
        save_file(response, folder, name)
    else:
        future = download_pool.submit(save_file, response, folder, name)
        pending_downloads[future] = destination


def download_content(url, cur_path, ignore_course_menu=True, verbose=True, name="file", course_id=None):
    url = resolve_blackboard_url(url)
    if url is None:
        return
    url = urldefrag(url)[0]
    query = parse_qs(urlsplit(url).query)
    section = query.get("courseTocLabel", [""])[0].strip().casefold()
    linked_course = query.get("course_id", [None])[0]
    if course_id is not None and linked_course not in (None, course_id):
        return
    course_id = course_id or linked_course
    if name.strip().casefold() == "general information" or section == "general information":
        return
    if url in visited_urls:
        return
    visited_urls.add(url)

    if len(pending_downloads) >= MAX_DOWNLOADS:
        finish_downloads()
    response = session.get(url, timeout=30, stream=True)
    try:
        response.raise_for_status()
        if resolve_blackboard_url(response.url) is None:
            raise RuntimeError("Blackboard sign-in expired. Refresh the cookies in headers.py.")
        redirected_course = parse_qs(urlsplit(response.url).query).get("course_id", [None])[0]
        if course_id is not None and redirected_course not in (None, course_id):
            return

        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type not in ("text/html", "application/xhtml+xml") or response.headers.get(
            "Content-Disposition", ""
        ).lower().startswith("attachment"):
            queue_download(response, cur_path, name)
            response = None  # The download worker owns and closes this response.
            return

        page_url = response.url
        soup = BeautifulSoup(response.content, "html.parser")
    finally:
        if response is not None:
            response.close()
    if soup.select_one('input[type="password"], #loginForm'):
        raise RuntimeError("Blackboard sign-in is required. Add current cookies to headers.py.")
    if verbose:
        print(f"Scanning: {cur_path}")
    page_heading = soup.find("h1")
    if page_heading and page_heading.get_text(" ", strip=True).casefold() == "general information":
        return
    content = soup.find("div", id="content") if ignore_course_menu else None
    content = content or soup

    for link in content.find_all(["a", "iframe", "frame"]):
        href = link.get("href") or link.get("src")
        if not href:
            continue
        target = resolve_blackboard_url(urljoin(page_url, href))
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
        if title.casefold() == "general information":
            continue
        folder = Path(cur_path)
        if parts.path.startswith("/webapps/blackboard/content/listContent"):
            folder /= safe_name(title)
        try:
            download_content(target, folder, name=title, course_id=course_id)
        except (requests.RequestException, OSError) as error:
            print(f"Failed: {title} ({error})", file=sys.stderr)


def download_file(url, path, name):
    download_content(url, path, name=name)


def main():
    global download_pool, download_errors
    if not course_links:
        print("Add the courses to download in course_links.py.", file=sys.stderr)
        return 1
    if not getattr(authentication, "cookies", {}) and not session.headers.get("Cookie"):
        print("Add your signed-in Blackboard cookies to headers.py.", file=sys.stderr)
        return 1

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "downloads"
    failed = False
    download_errors = False
    visited_urls.clear()
    try:
        with ThreadPoolExecutor(max_workers=MAX_DOWNLOADS) as pool:
            download_pool = pool
            for name, url in course_links.items():
                try:
                    starts_at_folder = urlsplit(url).path.startswith(
                        "/webapps/blackboard/content/listContent"
                    )
                    folder = output / safe_name(name)
                    if name.startswith("Maths Central / "):
                        section = name.removeprefix("Maths Central / ")
                        folder = output / "Maths Central" / safe_name(section)
                    download_content(url, folder, ignore_course_menu=starts_at_folder)
                except (requests.RequestException, OSError, RuntimeError) as error:
                    print(f"Failed: {name} ({error})", file=sys.stderr)
                    failed = True
    finally:
        try:
            finish_downloads(wait_for_all=True)
        finally:
            download_pool = None
    return int(failed or download_errors)


if __name__ == "__main__":
    sys.exit(main())
