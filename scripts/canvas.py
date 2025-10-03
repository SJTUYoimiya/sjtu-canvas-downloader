from bs4 import BeautifulSoup
from .sjtu_login import login

class CanvasHelper:
    def __init__(self, user: str, cookies_path: str = None):
        if not cookies_path:
            cookies_path = f'cookies_{user}.txt'
        self.session = login(
            "https://oc.sjtu.edu.cn/login/openid_connect", 
            "pwd", 
            cookies_path
        )
        self.subjects = self.get_subject_list()

    def get_subject_list(self) -> list[dict[str, int | str]]:
        """
        Get the id and name of all subjects from Canvas(oc.sjtu.edu.cn).

        Returns
        -------
        list[dict]
            A list of dictionaries, each containing 'id' and 'shortName' of a
            subject.
        """
        url = "https://oc.sjtu.edu.cn/api/v1/dashboard/dashboard_cards"
        res = self.session.get(url)
        res.raise_for_status()

        subject_ids = list()
        for subject in res.json():
            subject_ids.append({
                "id": subject.get('id'), 
                "name": subject.get('shortName')
            })
        return subject_ids

    def _http_request(self, 
                      method: str, 
                      url: str, 
                      **kwargs) -> tuple[str, dict]:
        """
        Perform a GET request and parse the first form in the response HTML.

        Parameters
        ----------
        method : str
            The HTTP method to use ('GET' or 'POST').
        url : str
            The URL to send the request to.
        **kwargs
            Additional arguments to pass to requests.get().

        Returns
        -------
        action : str
            The action URL of the form.
        data : dict
            A dictionary of input names and values from the form.
        """
        if method.upper() == 'GET':
            res = self.session.get(url, **kwargs)
        elif method.upper() == 'POST':
            res = self.session.post(url, **kwargs)
        else:
            raise ValueError("Unsupported HTTP method")

        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        form = soup.find('form')
        action = form.get('action')

        inputs = form.find_all('input')
        data = {input.get('name'): input.get('value') for input in inputs}
        return action, data
    
    def get_access_token(self, subject_id: int) -> str:
        """
        Get access token for a specific subject.

        Parameters
        ----------
        subject_id : int
            The ID of the subject to get the access token for.

        Returns
        -------
        access_token : str
            The access token for the specified subject.
        canvas_subject_id : int
            The Canvas course ID for the specified subject.
        """
        url = f"https://oc.sjtu.edu.cn/courses/{subject_id}/external_tools/8329"
        redi_url, data = self._http_request('GET', url)
        redi_url, data = self._http_request('POST', redi_url, data=data)

        res = self.session.post(redi_url, data=data, allow_redirects=False)
        res.raise_for_status()

        redi_url = res.headers.get('Location')
        query = redi_url.split('?')[1]

        url = "https://v.sjtu.edu.cn/jy-application-canvas-sjtu/lti3/getAccessTokenByTokenId"
        url += "?" + query
        res = self.session.get(url)
        res.raise_for_status()
        res_data = res.json()

        assert res_data.get('code') == '0', \
            res_data.get('message', 'Unknown error')

        access_token = res_data.get('data').get('token')
        canvas_subject_id = res_data.get('data').get('params').get('courId')

        return access_token, canvas_subject_id
    
    def refresh(self) -> list[dict[str, int | str]]:
        """
        Refresh the access tokens for all subjects.
        """
        for subject in self.subjects:
            subject_id = subject.get('id')
            access_token, canvas_subject_id = self.get_access_token(subject_id)
            subject['access_token'] = access_token
            subject['canvas_subject_id'] = canvas_subject_id
        
        return self.subjects
    

if __name__ == "__main__":
    helper = CanvasHelper("dingk")
    print(helper.refresh())
