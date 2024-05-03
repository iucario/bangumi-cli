import logging

import requests

from bangumi_cli import types
from bangumi_cli.settings import user_agent


class NotFoundError(Exception):
    pass


def get_me(token) -> types.User:
    api = 'https://api.bgm.tv/v0/me'
    header_auth = {'Authorization': f'Bearer {token}', 'User-Agent': user_agent}

    r = requests.get(api, headers=header_auth)
    if r.status_code != 200:
        logging.error(r.text)
        raise Exception('Failed to get user info')
    return r.json()


def get_subject(subject_id: int, limit: int = 100, offset: int = 0) -> types.Subject:
    api = f'https://api.bgm.tv/v0/subjects/{subject_id}'
    params = {'limit': limit, 'offset': offset}
    r = requests.get(api, params=params, headers={'User-Agent': user_agent})
    if r.status_code != 200:
        logging.error(r.text)
        raise Exception(r.json())
    return r.json()


def get_user_collection(token, username: str | int, subject_id: int) -> types.UserCollection:
    """Auth needed for private user collection"""
    api = f'https://api.bgm.tv/v0/users/{username}/collections/{subject_id}'
    r = requests.get(api, headers={'Authorization': f'Bearer {token}', 'User-Agent': user_agent})
    if r.status_code == 404:
        raise NotFoundError
    elif r.status_code != 200:
        logging.error(r.text)
        raise Exception(r.json())
    return r.json()


def get_user_collections(token,
                         username: str,
                         subject_type: int = 2,
                         type: int = 3,
                         limit: int = 30,
                         offset: int = 0) -> types.UserCollections:
    api = f'https://api.bgm.tv/v0/users/{username}/collections'
    r = requests.get(api,
                     params={
                         'subject_type': subject_type,
                         'type': type,
                         'limit': limit,
                         'offset': offset,
                     },
                     headers={
                         'Authorization': f'Bearer {token}',
                         'User-Agent': user_agent
                     })
    if r.status_code == 404:
        raise NotFoundError
    elif r.status_code != 200:
        logging.error(r.text)
        raise Exception(r.json())
    return r.json()


def get_user_subject(token, subject_id: int, limit: int = 100, offset: int = 0) -> types.UserEpisodes:
    api = f'https://api.bgm.tv/v0/users/-/collections/{subject_id}/episodes'
    params = {'limit': limit, 'offset': offset}
    headers = {'Authorization': f'Bearer {token}', 'User-Agent': user_agent}
    r = requests.get(api, params=params, headers=headers)
    if r.status_code != 200:
        logging.error(r.text)
        raise Exception(r.json())
    return r.json()


def get_user_episode(token: str, episode_id: int) -> types.UserEpisode:
    api = f'https://api.bgm.tv/v0/users/-/collections/-/episodes/{episode_id}'
    headers = {'Authorization': f'Bearer {token}', 'User-Agent': user_agent}
    r = requests.get(api, headers=headers)
    if r.status_code != 200:
        logging.error(r.text)
        raise Exception(r.json())
    return r.json()


def put_user_episode(token: str, episode_id: int, watch: bool = True) -> None:
    """Mark episode as watched or not watched
    
    Args:
        token (str): access token
        episode_id (int): Episode id
        watch (bool, optional): Mark as watched or not watched. Defaults to True.
    """

    data = {'type': 2} if watch else {'type': 0}
    api = f'https://api.bgm.tv/v0/users/-/collections/-/episodes/{episode_id}'
    headers = {'Authorization': f'Bearer {token}', 'User-Agent': user_agent}
    r = requests.put(api, headers=headers, json=data)
    if r.status_code != 204:
        logging.error(r.text)
        raise Exception(r.json())


def get_calendar() -> list[types.Calendar]:
    api = 'https://api.bgm.tv/calendar'
    r = requests.get(api, headers={'User-Agent': user_agent})
    if r.status_code != 200:
        logging.error(r.text)
        raise Exception(r.json())
    return r.json()


def search(
    keyword: str | None,
    sort: str,
    limit: int = 10,
    offset: int = 0,
    type: list[int] = [2],
    tags: list[str] = [],
    rating: tuple[int, int] = (0, 10),
    rank: tuple[int, int] = (1, 2000)) -> list[types.Subject]:
    """BUG: rating and rank should be and but it's or. Fix one side of the range."""

    api = f'https://api.bgm.tv/v0/search/subjects?limit={limit}&offset={offset}'
    data = {
        'keyword': keyword,
        'sort': 'rank',
        'limit': limit,
        'offset': offset,
        'filter': {
            'type': type,
            'tag': tags,
            'rating': [f">={rating[0]}"],
            'rank': [f"<={rank[1]}"],
        },
        'nsfw': False
    }
    r = requests.post(api, headers={'User-Agent': user_agent}, json=data)
    if r.status_code != 200:
        logging.error(r.text)
        raise Exception(r.json())
    res: types.SearchResult = r.json()
    return res['data']


def post_collection(token: str, subject_id: int, data: types.PostCollectionPayload) -> None:
    """Create collection."""
    api = f'https://api.bgm.tv/v0/users/-/collections/{subject_id}'
    headers = {'Authorization': f'Bearer {token}', 'User-Agent': user_agent}
    r = requests.post(api, headers=headers, json=data)
    if not r.ok:
        logging.error(r.text)
        raise Exception(r.json())


def patch_collection(token: str, subject_id: int, data: types.PatchCollectionPayload) -> None:
    """Update collection."""
    api = f'https://api.bgm.tv/v0/users/-/collections/{subject_id}'
    headers = {'Authorization': f'Bearer {token}', 'User-Agent': user_agent}
    r = requests.patch(api, headers=headers, json=data)
    if not r.ok:
        logging.error(r.text)
        raise Exception(r.json())
