"""
Helper for logging into Canvas(oc.sjtu.edu.cn) and getting the access tokens for 
each subject.

Classes
-------
CanvasHelper
    A helper class for logging into Canvas and retrieving access tokens for
    subjects.
CourseHelper
    A helper class for retrieving course information and video URLs for a
    specific subject in Canvas.

Examples
--------
```python
from canvas import CanvasHelper
helper = CanvasHelper("your_username")
subjects = helper.subjects
```
"""
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from .sjtu_login import login

class CanvasHelper:
    """
    Helper for logging into Canvas(oc.sjtu.edu.cn) and getting the access tokens
    for each subject.
    1. Log in to Canvas using jAccount OAuth2.0 Authentication.
    2. Get the list of subjects from the **Courses** sidebar.
    3. For each subject, simulate the process of clicking "Classroom Video New"
       button to get the access token.

    Parameters
    ----------
    method : str, optional
        The login method to use. Options are "pwd" for password login and "qr" 
        for QR code login. Default is "pwd".
    """
    def __init__(self, **kwargs):
        client = "https://oc.sjtu.edu.cn/login/openid_connect"
        self.session = login(client, **kwargs)
        self.refresh(True)

    @property
    def subjects(self) -> list[dict[str, int | str]]:
        if not hasattr(self, '_subjects'):
            self.refresh(True)
        return self._subjects

    def get_subject_list(self) -> list[dict[str, int | str]]:
        """
        Get all subjects for a user from the **Courses** sidebar in Canvas
        (oc.sjtu.edu.cn).

        Returns
        -------
        subjects : list of dict
            A list of subjects with their IDs, names, and account IDs.
            TODO: `account_id` may be helpful for filtering subjects, 
            more test samples are needed.
        """
        url = "https://oc.sjtu.edu.cn/api/v1/users/self/favorites/courses"
        res = self.session.get(url)
        res.raise_for_status()

        subjects = list()
        for subject in res.json():
            subjects.append({
                "id": subject['id'], 
                "name": subject['name'],
                "account": subject['account_id']
            })
        return subjects

    def _redirect_request(self, 
                      method: str, 
                      url: str, 
                      data: dict = None) -> tuple[str, dict]:
        """
        Make a request and parse the redirect form.

        Parameters
        ----------
        method : str
            The HTTP method to use ('GET' or 'POST').
        url : str
            The URL to send the request to.
        data : dict, optional
            The data to send in the request (for POST requests).

        Returns
        -------
        target_url : str
            The URL to redirect to.
        payload : dict
            The form data to send in the redirect request.
        """
        res = self.session.request(method, url, data=data)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, 'html.parser')
        form = soup.find('form')
        if form['id'] == "login_form":
                raise RuntimeError("Login required.")

        target_url = form['action']
        inputs = form.find_all('input')
        payload = {input_tag['name']: input_tag['value'] for input_tag in inputs}
        return target_url, payload

    def get_access_token(self, subject_id: int) -> tuple[str, str]:
        """
        Get the access token for a subject with the given ID.
        Simulate the process of clicking "Classroom Video New" button to
        redirect to *v.sjtu.edu.cn*
        1. Click the redirect link to obtain the login parameters for 
            *v.sjtu.edu.cn*
        2. Simulate the login and obtain authorization
        3. Obtain the course token ID
        4. Use the token ID to obtain the token

        Parameters
        ----------
        subject_id : int
            The ID of the subject to get the access token for.

        Returns
        -------
        access_token : str
            The access token for the subject.
        canvas_subject_id : str
            The Canvas subject ID.
        """
        # First redirect: to LTI tool
        url = f"https://oc.sjtu.edu.cn/courses/{subject_id}/external_tools/8329"
        url, payload = self._redirect_request('GET', url)  

        # Second redirect: login to v.sjtu.edu.cn
        url, payload = self._redirect_request('POST', url, data=payload)

        # Third redirect to get token ID
        res = self.session.post(url, data=payload, allow_redirects=False)
        res.raise_for_status()
        url = res.headers.get('Location')
        query = url.split('?')[1]

        url = "https://v.sjtu.edu.cn/jy-application-canvas-sjtu/lti3/getAccessTokenByTokenId"
        url += "?" + query
        res = self.session.get(url)
        res.raise_for_status()
        res = res.json()
        assert int(res['code']) == 0, res.get('message', 'Unknown error')

        data = res['data']
        access_token = data['token']
        canvas_subject_id = data['params']['courId']
        return access_token, canvas_subject_id

    def refresh(self, update_subjects: bool = False):
        """Refresh the access tokens for all subjects."""
        if not hasattr(self, '_subjects') or update_subjects:
            self._subjects = self.get_subject_list()

        # TODO: Parallel requests may speed up this process
        for subject in self._subjects:
            subject_id = subject['id']
            access_token, canvas_subject_id = self.get_access_token(subject_id)
            subject['access_token'] = access_token
            subject['canvas_subject_id'] = canvas_subject_id


class CourseHelper:
    """
    Get course information and video URLs for a specific subject in Canvas.
    1. Get the list of courses for the subject using the access token and
       Canvas subject ID.
    2. For each course, get the video download URLs.

    Parameters
    ----------
    access_token : str
        The access token for the subject.
    canvas_subject_id : str
        The Canvas subject ID.
    """
    def __init__(self,
                 access_token: str,
                 canvas_subject_id: str):
        self._token = access_token
        self._id = canvas_subject_id
    
    @property
    def courses(self) -> list[dict]:
        if not hasattr(self, '_courses'):
            self._courses = self.get_course_info()
        return self._courses

    @staticmethod
    def from_dict(data: dict) -> 'CourseHelper':
        """
        Load data from a local dictionary.

        Parameters
        ----------
        data : dict
            A dictionary containing the access token, canvas subject ID,
            and courses information.
        """
        helper = CourseHelper(
            access_token=data.get('access_token', ''),
            canvas_subject_id=data.get('canvas_subject_id', '')
        )
        helper._courses = data.get('courses', [])
        return helper

    def refresh(self):
        """Refresh all the courses information and download video URLs."""
        self._courses = self.get_course_info()
        for course in self._courses:
            download_urls = self.get_video_url(course['video_id'])
            course['download_urls'] = download_urls

    def update(self):
        """Only update the courses information without downloading video URLs."""
        if not hasattr(self, '_courses'):
            self.refresh()
            return

        updated = self.get_course_info()
        current = {c['id']: c for c in self._courses}
        for course in updated:
            cid = course['id']
            if cid in current and current[cid].get('download_urls', None):
                continue
            download_urls = self.get_video_url(course['video_id'])
            course['download_urls'] = download_urls 
            current[cid] = course
        self._courses = list(current.values())

    ## --------------------- Course Information Methods --------------------- ##
    def get_course_info(self) -> list[dict]:
        """Get the courses information for the subject."""
        url = "https://v.sjtu.edu.cn/jy-application-canvas-sjtu/directOnDemandPlay/findVodVideoList"
        payload = {"canvasCourseId": quote(self._id)}
        res = requests.post(url, json=payload, headers={'token': self._token})
        res.raise_for_status()
        res = res.json()
        if int(res['code']) == -1 or not res['data']:
            return list()

        data = res['data']
        courses = list()
        for course in data.get('records', []):
            courses.append({
                'id': course.get('courId'),
                'name': course.get('videoName'),
                'dt_start': course.get('courseBeginTime'),
                'dt_end': course.get('courseEndTime'),
                'video_id': course.get('videoId'),
            })
        return courses

    def get_video_url(self, video_id: str) -> dict[int, str]:
        """
        Get the download URLs of a video.

        Parameters
        ----------
        video_id : str
            The ID of the video to get URLs for.

        Returns
        -------
        videos : dict
            A dictionary with keys as channel numbers (0 or 1) and values as
            the corresponding video URLs.
            0: Classroom camera recording
            1: Computer screen recording
        """
        url = "https://v.sjtu.edu.cn/jy-application-canvas-sjtu/directOnDemandPlay/getVodVideoInfos"
        files = {
            "playTypeHls": (None, "true"),
            "isAudit": (None, "true"),
            "id": (None, video_id)
        }

        res = requests.post(url, files=files, headers={'token': self._token})
        res.raise_for_status()
        data = res.json().get('data')

        videos = dict()
        for video in data.get('videoPlayResponseVoList', []):
            channel = int(video.get('cdviViewNum')) != 0
            videos[int(channel)] = video.get('rtmpUrlHdv')
        return videos

    def get_transcripts(self, course_id: int, lang: str = '') -> list[dict]:
        """
        Get the original transcripts for a specific course in a given language.

        Parameters
        ----------
        course_id : int
            The ID of the course to get transcripts for.
        lang : str, optional
            The language of the transcripts to retrieve. If not specified, 
            defaults to 'res' (original language).

        Returns
        -------
        transcripts : list[dict]
            A list of transcripts with their start and end times, and content.
            Each transcript is represented as a dictionary with keys:
            - 'dt_start': Start time of the transcript segment.
            - 'dt_end': End time of the transcript segment.
            - 'content': The transcript text in the specified language.
        """
        url = "https://v.sjtu.edu.cn/jy-application-canvas-sjtu/transfer/translate/detail"
        payload = {
            'courseId': course_id,
            'platform': 1
        }
        res = requests.post(url,
                            json=payload,
                            headers={'token': self._token})
        res.raise_for_status()
        data = res.json().get('data')
        if not data:
            return list()

        transcripts = list()
        lang = lang if lang else 'res'
        for item in data.get('originalList', []):
            dt_start = item.get('bg')
            dt_end = item.get('ed')
            content = item.get(lang)
            transcripts.append({
                'dt_start': dt_start,
                'dt_end': dt_end,
                'content': content
            })
        return transcripts

if __name__ == "__main__":
    helper = CanvasHelper(method="pwd", cookie_path="")
    print(helper.subjects)
