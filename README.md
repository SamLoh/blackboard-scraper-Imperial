# Blackboard Scraper for Imperial

Downloads files from your Blackboard Original courses into `downloads/<course name>/`,
keeping the course's content folders. Existing filenames are skipped.

Requires Python 3.9+, `requests`, and `beautifulsoup4`.

1. Sign in at https://bb.imperial.ac.uk in your browser.
2. Keep your current Blackboard cookies in the local `cookies` dictionary in
   `headers.py`. An optional `headers` dictionary is also supported.
3. On the Courses page, scroll until the courses you want are loaded. Run
   `getCourseLinks.js` in the browser console and paste its printed
   `course_links = {...}` assignment into `course_links.py`. Remove entries
   you do not want to download.
4. Run `python scrape.py`.

To choose another download folder, run `python scrape.py "C:\path\to\downloads"`.

The scraper follows Blackboard content folders and file links. Lecture recordings
and external services such as Panopto need their own download methods. Refresh
your cookies if Blackboard asks you to sign in again.

Cookies grant access to your signed-in account. Keep them on your computer and
out of commits.
