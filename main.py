from scripts.canvas import CanvasHelper
from scripts.course_helper import CourseHelper
from scripts.downloader import download

helper = CanvasHelper("")   # 在这里填入 jAccount 用户名
subjects = helper.refresh()
for subject in subjects:
    course_helper = CourseHelper(
        access_token=subject['access_token'],
        canvas_subject_id=subject['canvas_subject_id']
    )
    courses = course_helper.refresh_courses()
    subject['courses'] = courses

# import json
# with open('subjects.json', 'w') as f:
#     json.dump(subjects, f, indent=4, ensure_ascii=False)

for subject in subjects:
    course_helper = CourseHelper.from_dict(subject)
    course_helper.save_transcript(f'./srt/{subject["name"]}')
    download(course_helper.courses, f'./videos/{subject["name"]}', classroom_only=True)
