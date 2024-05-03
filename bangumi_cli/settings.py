import importlib.metadata

version = importlib.metadata.version("bangumi_cli")

api_auth = 'https://bgm.tv/oauth/authorize'
client_id = 'bgm250163bec16210c2d'
app_secret = 'f4f057619facdba407afb48c9dce9114'
response_type = 'code'
user_agent = 'iucario/bangumi-cli'
host = 'http://localhost:9090/auth'
LOGIN_URL = f'{api_auth}?client_id={client_id}&response_type={response_type}&redirect_uri={host}'

