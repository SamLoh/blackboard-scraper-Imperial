# Blackboard Scraper for Imperial

Downloads files from your Blackboard Original courses into `downloads/<course name>/`.
It follows the course's content folders, keeps original filenames, and skips
filenames that already exist. Existing files are checked after reading response headers,
before reading the file body. Up to six workers check file headers and download
missing files in parallel. Folder discovery is sequential.
Quick Links are included, and links stay within each selected Blackboard course ID.
General Information sections are skipped during module scrapes. Maths Central has
two separate targets and destinations.

- [Past Examination Papers](https://bb.imperial.ac.uk/webapps/blackboard/content/listContent.jsp?course_id=_7508_1&content_id=_1087686_1)
  downloads into `downloads/Maths Central/Past Examination Papers/`.
- [Course Information](https://bb.imperial.ac.uk/webapps/blackboard/content/listContent.jsp?course_id=_7508_1&content_id=_1087552_1)
  downloads into `downloads/Maths Central/Course Information/`.

A target pointing directly at a content folder scans that folder's contents.
Names starting with `Maths Central / ` place that section inside the Maths Central
download folder. Existing General Information and other examinations material
moved there can be kept alongside these two sections.

1. **Open the repository in PowerShell.**

   Open PowerShell in your local copy of this repository. Install the two
   dependencies once with Python 3.9 or newer.

   ```powershell
   python -m pip install requests beautifulsoup4
   ```

2. **Sign in to Blackboard and choose courses.**

   Open [Imperial Blackboard](https://bb.imperial.ac.uk/ultra/course) and sign in.
   On the Courses page, choose list view and increase the items per page if needed.
   Scroll until the courses you want are loaded.

   Press **F12**, select **Console**, and run the contents of
   [getCourseLinks.js](getCourseLinks.js). Copy the printed
   `course_links = {...}` assignment into [course_links.py](course_links.py)
   and save it. Keep the entries for the courses you want to download.
   Start with one course to check the first live run.

   If you replace the whole file with fresh console output, append the following
   assignments to include Maths Central's two download sections.

   ```python
   course_links["Maths Central / Past Examination Papers"] = (
       "https://bb.imperial.ac.uk/webapps/blackboard/content/listContent.jsp?course_id=_7508_1&content_id=_1087686_1"
   )
   course_links["Maths Central / Course Information"] = (
       "https://bb.imperial.ac.uk/webapps/blackboard/content/listContent.jsp?course_id=_7508_1&content_id=_1087552_1"
   )
   ```

3. **Copy the Cookie request-header value.**

   Keep DevTools open and select **Network**. Click the crossed-circle icon
   beside the recording button to clear the request list. Make sure recording
   is active, then enter `listContent.jsp` in the **Filter** box.

   Click a course title on the Blackboard page. If the request list stays empty,
   refresh while inside the course.

   Click a matching request with **Status 200** and a Request URL on
   `https://bb.imperial.ac.uk`. In its **Headers** tab, expand
   **Request Headers**, find **Cookie**, and copy its value.

   It looks like `name=value; another_name=another_value`.
   This is the only Network value the scraper needs for its cookie configuration.
   [Chrome's guide to request headers](https://developer.chrome.com/docs/devtools/network/reference#headers)

4. **Paste that value into headers.py.**

   Open [headers.py](headers.py) in your editor. Paste the copied text on the
   empty line between the triple quotes.

   ```python
   cookie_header = """
   name=value; another_name=another_value
   """
   ```

   The example values above are placeholders. Keep the rest of the file and save
   it. The code below the quotes automatically converts the text into cookies
   for the scraper. It also accepts a copied line starting with `Cookie:`.

   Cookies grant access to your signed-in account. Keep them local. This
   repository tracks `headers.py`, so clear the pasted value before committing
   or sharing that file.

5. **Run the scrape.**

   From the repository folder, run the following command.

   ```powershell
   python scrape.py
   ```

   The default destination is the `downloads` folder beside `scrape.py`.
   To choose another destination, provide its path.

   ```powershell
   python scrape.py "C:\path\to\downloads"
   ```

6. **Check the files.**

   `Scanning` identifies a course folder being read. `Downloaded` identifies a
   saved file, `Already exists` identifies a filename being skipped, and
   `Failed` reports an error.

   Open a few downloaded files after the first course. You can then add more
   course entries and run the command again. Press **Ctrl+C** to stop.

If the scraper reports that sign-in is required or expired, repeat steps 3 and 4
with a current Cookie value. If it reports missing courses, check that
`course_links.py` contains a non-empty `course_links = {...}` assignment.

Lecture recordings and files hosted on external services such as Panopto require
those services' download methods. Live scraping depends on your current
Blackboard access and session.
