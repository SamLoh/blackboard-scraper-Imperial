# Replace this module dictionary with the output from getCourseLinks.js.
# Keep only the courses you actually need before running the scraper.
course_links = {
    "MATH40002 - Analysis 1 2025-2026": "https://bb.imperial.ac.uk/webapps/blackboard/execute/courseMain?course_id=_46862_1",
    "MATH40003 - Linear Algebra and Groups 2025-2026": "https://bb.imperial.ac.uk/webapps/blackboard/execute/courseMain?course_id=_46809_1",
    "MATH40004 - Calculus and Applications 2025-2026": "https://bb.imperial.ac.uk/webapps/blackboard/execute/courseMain?course_id=_46772_1"
}

# Keep these Maths Central assignments below the module dictionary.
# These sections are optional. Comment out either assignment if you do not need it.
course_links["Maths Central / Past Examination Papers"] = "https://bb.imperial.ac.uk/webapps/blackboard/content/listContent.jsp?course_id=_7508_1&content_id=_1087686_1"
course_links["Maths Central / Course Information"] = "https://bb.imperial.ac.uk/webapps/blackboard/content/listContent.jsp?course_id=_7508_1&content_id=_1087552_1"
