import getpass
import time
from io import BytesIO
import requests
from requests.cookies import RequestsCookieJar
import numpy as np
from PIL import Image

from .constants import HEADERS

## -------------------------------- Captcha -------------------------------- ##
def remove_padding(data: np.ndarray) -> np.ndarray:
    """
    Remove padding (rows and columns of all 1s) from a binary numpy array.
    
    Parameters
    ----------
    data : np.ndarray
        A 2D binary numpy array where 1 represents white pixels and 0 represents
        black pixels.

    Returns
    -------
    np.ndarray
        The input array with padding removed.
    """
    row_cond = ~np.all(data == 1, axis=1)
    row_idx = np.where(row_cond)[0]
    if len(row_idx) > 0:
        data = data[row_idx[0]: row_idx[-1]+1, :]

    col_cond = ~np.all(data == 1, axis=0)
    col_idx = np.where(col_cond)[0]
    if len(col_idx) > 0:
        data = data[:, col_idx[0]: col_idx[-1]+1]

    return data

def print_captcha_in_console(image: Image) -> None:
    """
    Print the captcha image in the console using ASCII characters.

    Parameters
    ----------
    image : PIL.Image
        The captcha image to be printed.
    """
    image = image.convert("L")
    data = np.array(image)
    data = (data - data.min()) / (data.max() - data.min())
    data = (data > 0.5).astype(int)
    data = remove_padding(data)
    for row in data:
        print("".join(" " if x else "#" for x in row))


## --------------------------------- Login --------------------------------- ##
def get_captcha_image(url: str, uuid: str) -> Image:
    """
    Get the captcha image from the server.

    Parameters
    ----------
    url : str
        The referer URL for the request, which is the redirect URL from the
        initial login attempt.
    uuid : str
        The UUID parameter for the captcha request.

    Returns
    -------
    Image
        The captcha image as a PIL Image object.
    """
    res = requests.get(
        "https://jaccount.sjtu.edu.cn/jaccount/captcha",
        params={"uuid": uuid, "t": time.time_ns()//1000000},
        headers={"Referer": url, **HEADERS},
    )
    res.raise_for_status()
    image = Image.open(BytesIO(res.content))
    return image

def send_login_request(
        user: str, pwd: str, captcha: str, params: dict
    ) -> tuple[dict, RequestsCookieJar]:
    """
    Send a login post request to the server.
    
    Parameters
    ----------
    user : str
        The username for login.
    pwd : str
        The password for login.
    captcha : str
        The captcha string entered by the user.
    params : dict
        Additional parameters required for the login request, including UUID.

    Returns
    -------
    data: dict
        The JSON response from the server.
    cookies: requests.cookies.RequestsCookieJar
        The cookies set by the server upon login.
    """
    url = "https://jaccount.sjtu.edu.cn/jaccount/ulogin"
    payload = {
        "user": user,
        "pass": pwd,
        "captcha": captcha,
        "lt": "p",
        **params
    }

    res = requests.post(url, data=payload, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return res.json(), res.cookies

def parse_login_state(url: str, data: dict):
    """
    Parse the login state from the server response.
    
    Parameters
    ----------
    url : str
        The referer URL for the request, which is the redirect URL from the
        initial login attempt.
    data : dict
        The JSON response from the server.

    Returns
    -------
    int
        0 if login is successful,
        1 if username or password is incorrect,
        2 if captcha is incorrect.

    Raises
    ------
    Exception
        If an unknown error occurs.
    """
    if int(data.get('errno', 1)) == 0:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return 0
    else:
        err_code = data.get('code', '')
        if err_code == "WRONG_USER_OR_PASSWORD":
            print("Incorrect username or password.")
            return 1
        elif err_code == "WRONG_CAPTCHA":
            print("Incorrect captcha.")
            return 2
        else:
            raise Exception(f"Unknown error: {data}")

def login_with_pwd(url: str, params: dict) -> RequestsCookieJar:
    """
    Perform login using username, password, and captcha.
    
    Parameters
    ----------
    url : str
        The referer URL for the request, which is the redirect URL from the
        initial login attempt.
    params : dict
        Additional parameters required for the login request, including UUID.

    Returns
    -------
    requests.cookies.RequestsCookieJar
        The cookies set by the server upon successful login.
    """
    current_user = ''
    while True:
        user = input(f"Enter username{('(' + current_user + ')') if current_user else ''}: ")
        if user:
            current_user = user
        elif current_user:
            user = current_user
            print(f"Using username: {user}")

        pwd = getpass.getpass("Enter password: ")

        while True:
            captcha_img = get_captcha_image(url, params.get("uuid"))
            print_captcha_in_console(captcha_img)
            captcha = input("Enter captcha: ")
            res, cookies = send_login_request(user, pwd, captcha, params)
            state_code = parse_login_state(url, res)
            if state_code == 0:
                return cookies
            elif state_code == 1:
                break
            elif state_code == 2:
                continue
