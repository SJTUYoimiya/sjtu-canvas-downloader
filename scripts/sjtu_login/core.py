import os
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

from .cookies_manager import load_cookies, save_cookies
from .constants import HEADERS

def login_attempt(client: str, cookies: dict):
    session = requests.Session()
    res = session.get(client, headers=HEADERS, cookies=cookies, timeout=10)
    res.raise_for_status()

    if res.status_code != 200:
        raise requests.HTTPError(
            f"Login failed with status code: {res.status_code}"
        )

    parsed = urlparse(res.url)
    if parsed.netloc != 'jaccount.sjtu.edu.cn':
        print("Login successful!")
        return {'code': 200, 'data': {'session': session}}
    else:
        params = parse_qs(parsed.query)
        soup = BeautifulSoup(res.text, 'html.parser')
        link: str = soup.find('a', attrs={'id': 'firefox_link'}).get('href', '')
        uuid = parse_qs(urlparse(link).query).get('uuid', [''])[0]
        return {
            'code': 401,
            'data': {
                'url': res.url,
                'params': {'uuid': uuid, **params}
            }
        }

def login(client: str, method: str, cookie_path: os.PathLike = None) -> requests.Session:
    """
    Main framework for logging in to SJTU jAccount OAUTH2.0 authentication.

    Parameters
    ----------
    client : str
        The client URL to authenticate against.
    method : str
        The login method, either 'pwd' for password or 'qr' for QR code.
        Currently, only 'pwd' is implemented.
    cookie_path : os.PathLike, optional
        Path to save/load cookies, by default None.
        If None, cookies are not saved or loaded.

    Returns
    -------
    requests.Session
        An authenticated requests session.

    Raises
    ------
    Exception
        If login fails or an unknown response code is received.
    """
    cookies = load_cookies(cookie_path)
    res = login_attempt(client, cookies)
    
    if res.get('code') == 200:
        print("Logged in with cookies.")
        return res.get('data').get('session')
    elif res.get('code') == 401:
        print("Login required, please proceed with authentication.")
        data = res.get('data', {})

        if method == 'pwd':
            from .pwd_login import login_with_pwd
            cookies = login_with_pwd(data.get('url', ''), data.get('params', {}))
            print("Logged in with password.")
        elif method == 'qr':
            raise Exception("QR code login not implemented yet.")
        
        if cookie_path:
            save_cookies(cookies, cookie_path)
        session = requests.Session()
        session.cookies.update(cookies)
        return session
    else:
        raise Exception("Unknown response code.")

if __name__ == "__main__":
    session = login('https://my.sjtu.edu.cn', 'pwd', 'cookies.txt')
