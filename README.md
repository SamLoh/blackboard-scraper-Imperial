# Blackboard Scraper for Imperial

Download your Imperial Blackboard course files and selected Maths Central resources
into a local `downloads` folder. Reruns skip files with matching filenames.

You need **Python 3.9 or newer**, Chrome, and access to Blackboard.

1. **Install the dependencies**

   Open PowerShell in this repository's folder and run the following command once.

   ```powershell
   python -m pip install requests beautifulsoup4
   ```

2. **Choose what to download**

   - Sign in to [Imperial Blackboard](https://bb.imperial.ac.uk/ultra/course).
   - Choose list view and increase the items per page. Scroll through the list to
     load the courses you want.
   - Press **F12** and open **Console**.
   - Open [getCourseLinks.js](getCourseLinks.js), copy its contents into the Console,
     and press **Enter**.
   - Copy the printed text starting with `course_links = {`.

   Open [course_links.py](course_links.py). Replace the module dictionary, from
   `course_links = {` through its closing `}`, with the copied output.

   **Only keep course links you actually need.** The generated list can include
   every loaded course. Remove unwanted entries before saving the file. Every
   course left in the dictionary will be checked and its available files
   downloaded. Courses can include videos and datasets as well as notes.

   **Keep the Maths Central assignments below the module dictionary and enable
   only the sections you need.** Each active assignment adds a whole section to
   the run. Put `#` at the start of either assignment to exclude that section.

   The two optional sections are listed below. Past Examination Papers includes
   the shared collection across all years.

   - [Past Examination Papers](https://bb.imperial.ac.uk/webapps/blackboard/content/listContent.jsp?course_id=_7508_1&content_id=_1087686_1)
   - [Course Information](https://bb.imperial.ac.uk/webapps/blackboard/content/listContent.jsp?course_id=_7508_1&content_id=_1087552_1)

   The supplied dictionary contains three Year 1 examples. For a single-course
   test, keep one module entry and comment out the two Maths Central assignments.

3. **Add your current sign-in cookie**

   In the same Chrome window where you signed in, open DevTools with **F12**.

   - Select **Network**.
   - Click the crossed-circle icon beside the recording button to clear the list.
     Make sure recording is active.
   - Type `listContent.jsp` into **Filter**.
   - Click a course title on the Blackboard page. Refresh inside the course if
     the request list stays empty.
   - Select a matching request with **Status 200** and a Request URL on
     `https://bb.imperial.ac.uk`.
   - Open **Headers**, expand **Request Headers**, find **Cookie**, and copy its whole value.

   Open [headers.py](headers.py). Paste the value between the triple quotes.

   ```python
   cookie_header = """
   PASTE_YOUR_COOKIE_VALUE_HERE
   """
   ```

   Keep the rest of the file and save it. The Cookie value is the only value
   needed from the Network tab.

   **Keep the cookie private.** It grants access to your signed-in session.
   Clear it from `headers.py` before committing or sharing the file. Use
   Blackboard's **Sign Out** when you have finished scraping.

4. **Run the scraper**

   From the repository folder, run the following command.

   ```powershell
   python scrape.py
   ```

   Files are saved beside `scrape.py` in this structure.

   ```text
   downloads/
     <course name>/
     Maths Central/
       Past Examination Papers/
       Course Information/
   ```

   To choose a different destination, pass its path.

   ```powershell
   python scrape.py "C:\path\to\downloads"
   ```

   Press **Ctrl+C** to stop. To run it again, use the same command.

5. **Check the results**

   | Message | Meaning |
   |---|---|
   | `Scanning` | Reading a course folder |
   | `Downloaded` | Saved a file |
   | `Already exists` | Skipped a matching filename in that destination |
   | `Already queued` | Another worker is already saving that filename |
   | `Failed` | The request or file download encountered an error |

   Open a few downloaded files to check they work.

**Common problems**

- **Missing `requests` or `bs4`** - repeat step 1.
- **Missing course links** - check that the module dictionary in `course_links.py`
  contains the courses you selected.
- **Sign-in required or expired** - repeat step 3 with a fresh Cookie value.
- **404 error** - Blackboard could not provide that link.
- **500 error** - Blackboard returned a server error. Try that link again later.

**Download behaviour**

- `MAX_WORKERS` in [scrape.py](scrape.py) controls parallel file checks and downloads.
  The default is **3**, a conservative limit for everyday laptop use.
  Set it to **1** for serial file checks and downloads. Folder discovery runs
  sequentially.
- Existing filenames are checked after reading the response headers, before
  reading the file body.
- Module scrapes include Quick Links and skip General Information.
- Learning modules are followed through their contents lists, next-page links,
  and embedded frames. Quoted navigation URLs in link handlers are read without
  running JavaScript.
- Pages that build their links entirely with JavaScript and external learning
  tools may still need manual downloads. If files are missing, copy the section
  link address so its page type can be checked.
- Each target stays within its Blackboard course or organisation ID.
- The Maths Central targets scan their selected sections and subfolders.
- Files hosted on services such as Panopto use those services' download options.

For help finding the Cookie header, see
[Chrome's request-header guide](https://developer.chrome.com/docs/devtools/network/reference#headers).
