import os.path
from http.cookiejar import LWPCookieJar, LoadError
from requests.cookies import RequestsCookieJar

def load_cookies(cookie_path: os.PathLike) -> dict[str, str] | None:
    """
    Load JAAuthCookie from local cookie file.

    Parameters
    ----------
    cookie_path : os.PathLike
        Path to the cookie file.

    Returns
    -------
    dict[str, str] | None
        A dictionary containing the JAAuthCookie if found, otherwise None.
    """
    if cookie_path and os.path.exists(cookie_path):
        jar = LWPCookieJar(cookie_path)
        try:
            jar.load(ignore_discard=True)
        except LoadError:
            return
        cookies = {cookie.name: cookie.value for cookie in jar}
        
        if cookies.get('JAAuthCookie', None):
            return {'JAAuthCookie': cookies.get('JAAuthCookie')}

    return

def save_cookies(cookies: RequestsCookieJar, cookie_path: os.PathLike) -> None:
    """
    Save JAAuthCookie to local cookie file.

    Parameters
    ----------
    cookies : RequestsCookieJar
        The cookies to be saved.
    cookie_path : os.PathLike
        Path to the cookie file.
    """
    jar = LWPCookieJar(cookie_path)
    for cookie in cookies:
        if cookie.name == 'JAAuthCookie':
            jar.set_cookie(cookie)
            break
    jar.save(ignore_discard=True, ignore_expires=True)
    print(f"Cookies saved to {cookie_path}")
