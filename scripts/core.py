import os.path
import time
from .utils import aria2, parse_srt
from .canvas import CanvasHelper, CourseHelper


class Manager:
    def __init__(self, **kwargs):
        self.subjects: list[dict] = []
        self.last_update_at: float | None = None
        self._cour_helpers: dict[int, CourseHelper] = {}

        if len(kwargs) > 0:
            self._subj_helper = CanvasHelper(**kwargs)
            self.subjects = self._subj_helper.subjects
            self.refresh()

    @staticmethod
    def from_json(filepath: os.PathLike) -> 'Manager':
        """
        Load Manager instance from a JSON file.
        The JSON file should contain 'subjects' and 'last_update_at' fields.

        Parameters
        ----------
        filepath : os.PathLike
            Path to the JSON file.

        Returns
        -------
        Manager
            An instance of Manager populated with data from the JSON file.
        """
        import json

        with open(filepath, 'r') as f:
            data = json.load(f)

        mgr = Manager()
        mgr.subjects = data.get('subjects', [])
        mgr.last_update_at = data.get('last_update_at', None)
        mgr._cour_helpers = {
            subj['id']: CourseHelper(
                subj['access_token'], subj['canvas_subject_id']
            ) for subj in mgr.subjects
        }
        return mgr

    def refresh(self):
        """Refresh all the courses information for all subjects."""
        for subj in self.subjects:
            helper = CourseHelper(
                subj['access_token'], subj['canvas_subject_id']
            )
            self._cour_helpers[subj['id']] = helper

            helper.update()
            subj['courses'] = helper.courses
            subj['total'] = len(helper.courses)
        self.last_update_at = time.time()

    def download(self, 
               courses: dict[int, list], 
               dirpath: os.PathLike, 
               with_screen_record: bool = False):
        subjects = {subj['id']: subj.copy() for subj in self.subjects}
        for subj in subjects.values():
            subj['courses'] = {c['id']: c for c in subj['courses']}

        os.makedirs(dirpath, exist_ok=True)
        download_txt = self._generate_aria2_txt(
            courses, subjects, with_screen_record
        )
        with open(os.path.join(dirpath, 'download.txt'), 'w') as f:
            f.write(download_txt)

        for subj_id, course_ids in courses.items():
            subj = subjects.get(subj_id)
            helper = self._cour_helpers.get(subj_id)
            os.makedirs(os.path.join(dirpath, subj['name']), exist_ok=True)

            for cid in course_ids:
                course = subj['courses'].get(cid)
                transcripts = helper.get_transcripts(cid)
                srt_content = parse_srt(transcripts)
                with open(
                    os.path.join(
                        dirpath, subj['name'], f"{course['name']}_0.srt"
                    ), 'w', encoding='utf-8'
                ) as f:
                    f.write(srt_content)

        aria2(dirpath)

    def _generate_aria2_txt(self, 
                            course_ids: dict[int, list], 
                            subjects: dict[int, dict],
                            with_screen_record: bool = False) -> str:
        """
        Generate aria2 download.txt content for the specified courses.
        """
        download_queue = []
        for subj_id, course_id_list in course_ids.items():
            subj = subjects.get(subj_id)
            subj_name = subj.get('name')
            for course_id in course_id_list:
                course = subj['courses'].get(course_id)
                course_name = course.get('name')
                for k, v in course.get('download_urls', {}).items():
                    if (not with_screen_record) and int(k) == 1:
                        continue

                    exf = v.split('?')[0].split('.')[-1]
                    output_path = f"{subj_name}/{course_name}_{k}.{exf}"
                    download_queue.append((v, output_path))

        download_queue = [
            f"{url}\n  out={path}\n" for url, path in download_queue
        ]
        return '\n'.join(download_queue)
