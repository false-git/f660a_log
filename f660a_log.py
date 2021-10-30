"""F660Aの通信量データを取る."""
import configparser
import hashlib
import http.client
import logging
import random
import re
import requests  # type: ignore
import typing as typ
from bs4 import BeautifulSoup  # type: ignore


def enable_http_debug() -> None:
    """httpのデバッグを有効にする.

    see: https://stackoverflow.com/questions/10588644/how-can-i-see-the-entire-http-request-thats-being-sent-by-my-python-application
    """
    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def main(host: str, username: str, password: str):
    """メイン.

    Args:
        host: ホスト名又はIPアドレス
        username: ユーザ名
        password: パスワード
    """
    url: str = f"http://{host}/"
    rlogintoken: re.Pattern = re.compile(r"creatHiddenInput\(\"Frm_Logintoken\", *\"(\d+)\"\)")
    rloginchecktoken: re.Pattern = re.compile(r"creatHiddenInput\(\"Frm_Loginchecktoken\", *\"(\d+)\"\)")

    s: requests.Session = requests.Session()
    res: requests.Response = s.get(url)

    m: typ.Optional[re.Match] = rlogintoken.search(res.text)
    if m is None:
        print("error 1")
        return 1
    logintoken: str = m[1]
    m = rloginchecktoken.search(res.text)
    if m is None:
        print("error 2")
        return 2
    loginchecktoken: str = m[1]
    pwd_random: int = round(random.random() * 89999999) + 10000000
    before_password = hashlib.md5(f"{password}{pwd_random}".encode("utf-8")).hexdigest()
    params: typ.Dict[str, str] = {}

    params["action"] = "login"
    params["Username"] = username
    params["Password"] = before_password
    params["Frm_Logintoken"] = logintoken
    params["UserRandomNum"] = str(pwd_random)
    params["Frm_Loginchecktoken"] = loginchecktoken

    res2: requests.Response = s.post(url, data=params, allow_redirects=False)
    if res2.status_code != 302:
        print("error 3")
        return 3

    res3: requests.Response = s.get(f"{url}getpage.gch?pid=1002&nextpage=pon_status_lan_link_info_t.gch")
    if res3.status_code != 200:
        print("error 4")
        return 4

    columns: typ.List[str] = [
        "ポート名",
        "受信したデータ量(byte)",
        "受信したパケットの総数",
        "マルチキャストパケットの受信数",
        "ブロードキャストパケットの受信数",
        "送信したデータ量(byte)",
        "送信されたパケットの総数",
        "マルチキャストパケットの送信数",
        "ブロードキャストパケットの送信数",
    ]
    indexdic: typ.Dict[str, int] = {}
    for i, c in enumerate(columns):
        indexdic[c] = i
    print(", ".join(columns))
    soup = BeautifulSoup(res3.text, "html.parser")
    index: int = -1
    values: typ.List = []
    for td in soup.find_all("td"):
        if index != -1:
            values[index] = td.text.strip()
            index = -1
        else:
            index = indexdic.get(td.text.strip(), -1)
            if index == 0:
                if len(values) > 0:
                    print(", ".join(values))
                values = [""] * len(columns)
    if len(values) > 0:
        print(", ".join(values))


if __name__ == "__main__":
    inifile: configparser.ConfigParser = configparser.ConfigParser()
    inifile.read("f660a.ini", "utf-8")
    hostip: str = inifile.get("F660A", "hostip", fallback="192.168.1.1")
    username: str = inifile.get("F660A", "username", fallback="admin")
    password: str = inifile.get("F660A", "password")
    main(hostip, username, password)
