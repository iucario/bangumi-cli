import http.server
import os
import socketserver
import urllib.parse
from typing import TypedDict

import requests
import yaml

from bangumi_cli.base_logger import logger
from bangumi_cli.settings import LOGIN_URL, app_secret, client_id, host, user_agent


class Credential(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str
    user_id: int


class HTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        code = self.parse_code(self.path)
        self.wfile.write(self._create_html(code).encode())

    def parse_code(self, path):
        query = urllib.parse.urlparse(path).query
        code = urllib.parse.parse_qs(query)['code'][0]
        return code

    def _create_html(self, code: str) -> str:
        """Create a simple html page to display the code"""
        html = f"""
        <html><head><title>bgm-cli</title><style>
        body {{text-align: center;}}
        </style></head>
        <body>
        <h1>Copy the code to the terminal</h1>
        <h2>{code}</h2>
        </body></html>
        """
        return html


def handle_one_request():
    PORT = 9090
    Handler = HTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), Handler)
    httpd.handle_request()
    httpd.server_close()


def get_access_token(code: str) -> Credential:
    api = 'https://bgm.tv/oauth/access_token'
    grant_type = 'authorization_code'
    r = requests.post(api,
                      headers={'User-Agent': user_agent},
                      data={
                          'client_id': client_id,
                          'client_secret': app_secret,
                          'grant_type': grant_type,
                          'code': code,
                          'redirect_uri': host,
                      })
    if r.status_code != 200:
        logger.error(r.text)
        raise RuntimeError('Failed to get access token')
    return r.json()


def wait_user_input():
    print('Open this URL in browser and login:\n', LOGIN_URL)
    handle_one_request()
    code = input('Paste the code here: ')
    print('code:', code)
    return code


def refresh_access_token(token):
    api = 'https://bgm.tv/oauth/access_token'
    grant_type = 'refresh_token'
    r = requests.post(api,
                      headers={'User-Agent': user_agent},
                      data={
                          'client_id': client_id,
                          'client_secret': app_secret,
                          'grant_type': grant_type,
                          'refresh_token': token,
                          'redirect_uri': host,
                      })
    if r.status_code != 200:
        logger.error(r.text)
        return None
    return r.json()


def get_token_status(token):
    api = 'https://bgm.tv/oauth/token_status'
    r = requests.post(api, headers={'User-Agent': user_agent}, params={'access_token': token})
    if r.status_code != 200:
        logger.error(r.text)
        return None
    return r.json()


def store_token(data: Credential):
    path = os.path.expanduser('~/.config/bangumi/auth.yaml')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        yaml.dump(data, f)


def load_token() -> Credential:
    """Load credentials from ~/.config/bangumi/auth.yaml"""
    path = os.path.expanduser('~/.config/bangumi/auth.yaml')
    if not os.path.exists(path):
        raise FileNotFoundError(f'Config not foundL {path}')
    with open(path, 'r') as f:
        return yaml.safe_load(f)
