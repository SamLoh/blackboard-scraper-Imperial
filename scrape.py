import mimetypes
import re
import sys
from concurrent.futures import ALL_COMPLETED, FIRST_COMPLETED, ThreadPoolExecutor, wait
from email.message import Message
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urldefrag, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

import headers as authentication
from blackboard_urls import resolve_blackboard_url
from course_links import course_links


MAX_WORKERS = 3
visited_urls = set()
download_pool = None
pending_downloads = {}
download_errors = False
active_destinations = set()
destination_lock = Lock()


def make_session():
    connection = requests.Session()
    connection.headers.update(getattr(authentication, "headers", {}))
    for cookie_name, cookie_value in getattr(authentication, "cookies", {}).items():
        connection.cookies.set(cookie_name, cookie_value, domain="bb.imperial.ac.uk", path="/")
    return connection


session = make_session()


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
        with destination_lock:
            if destination.exists():
                print(f"Already exists: {destination}")
                return
            if destination in active_destinations:
                print(f"Already queued: {destination}")
                return
            active_destinations.add(destination)

        temporary = destination.with_name(destination.name + ".part")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        handle.write(chunk)
            temporary.replace(destination)
            print(f"Downloaded: {destination}")
        finally:
            try:
                temporary.unlink(missing_ok=True)
            finally:
                with destination_lock:
                    active_destinations.discard(destination)


def finish_downloads(wait_for_all=False):
    global download_errors
    while pending_downloads:
        completed, _ = wait(
            pending_downloads,
            return_when=ALL_COMPLETED if wait_for_all else FIRST_COMPLETED,
        )
        pages = []
        for future in completed:
            description = pending_downloads.pop(future)
            try:
                page = future.result()
                if page is not None:
                    pages.append(page)
            except (requests.RequestException, OSError, RuntimeError) as error:
                print(f"Failed: {description} ({error})", file=sys.stderr)
                download_errors = True
        for page in pages:
            try:
                process_page(*page)
            except (requests.RequestException, OSError, RuntimeError) as error:
                print(f"Failed: {page[0]} ({error})", file=sys.stderr)
                download_errors = True
        if not wait_for_all:
            break


def queue_download(response, folder, name):
    destination = file_destination(response, folder, name)
    if destination.exists():
        response.close()
        print(f"Already exists: {destination}")
    elif download_pool is None:
        save_file(response, folder, name)
    else:
        future = download_pool.submit(save_file, response, folder, name)
        pending_downloads[future] = destination


def check_response(response, course_id):
    response.raise_for_status()
    if resolve_blackboard_url(response.url) is None:
        raise RuntimeError("Blackboard sign-in expired. Refresh the cookies in headers.py.")
    redirected_course = parse_qs(urlsplit(response.url).query).get("course_id", [None])[0]
    return course_id is None or redirected_course in (None, course_id)


def is_file_response(response):
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    return content_type not in ("text/html", "application/xhtml+xml") or response.headers.get(
        "Content-Disposition", ""
    ).lower().startswith("attachment")


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

    while len(pending_downloads) >= MAX_WORKERS:
        finish_downloads()
    if download_pool is not None and urlsplit(url).path.startswith("/bbcswebdav/"):
        future = download_pool.submit(download_file, url, cur_path, name, course_id)
        pending_downloads[future] = f"{cur_path}/{name}"
        return

    response = session.get(url, timeout=30, stream=True)
    try:
        if not check_response(response, course_id):
            return
        if is_file_response(response):
            queue_download(response, cur_path, name)
            response = None  # The download worker owns and closes this response.
            return
        page_url = response.url
        body = response.content
    finally:
        if response is not None:
            response.close()
    process_page(page_url, body, cur_path, course_id, ignore_course_menu, verbose)


def process_page(page_url, body, cur_path, course_id=None, ignore_course_menu=True, verbose=True):
    soup = BeautifulSoup(body, "html.parser")
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


def download_file(url, path, name, course_id=None):
    url = resolve_blackboard_url(url)
    if url is None:
        return
    with make_session() as connection:
        with connection.get(url, timeout=30, stream=True) as response:
            if not check_response(response, course_id):
                return
            if is_file_response(response):
                save_file(response, path, name)
                return
            # An HTML file viewer is handed back to sequential folder discovery.
            return response.url, response.content, path, course_id


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
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        download_pool = pool
        try:
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
