(() => {
    const courses = {};
    for (const link of document.querySelectorAll('a[id^="course-link-_"]')) {
        const courseId = link.id.replace("course-link-", "");
        const title = link.querySelector("h4")?.textContent || link.textContent;
        const name = title.replace(/Original Course View/g, "").trim();
        if (name) {
            courses[name] = "https://bb.imperial.ac.uk/webapps/blackboard/execute/courseMain?course_id="
                + encodeURIComponent(courseId);
        }
    }
    console.log("course_links = " + JSON.stringify(courses, null, 4));
})();
