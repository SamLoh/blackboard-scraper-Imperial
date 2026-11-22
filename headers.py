# Paste your Blackboard Cookie value between the triple quotes for a local run.
# Clear the value before committing or sharing this file.
cookie_header = """

"""

cookie_header = cookie_header.strip()
if cookie_header.lower().startswith("cookie:"):
    cookie_header = cookie_header.split(":", 1)[1].strip()

headers = {}
cookies = dict(
    item.strip().split("=", 1)
    for item in cookie_header.split(";")
    if "=" in item
)
