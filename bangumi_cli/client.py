import time

from bangumi_cli import api, collection
from bangumi_cli.api import get_me, get_subject, get_user_collections, put_user_episode
from bangumi_cli.auth import (Credential, get_access_token, get_token_status, load_token, refresh_access_token,
                              store_token)
from bangumi_cli.base_logger import logger
from bangumi_cli.types import Episode, PatchCollectionPayload, PostCollectionPayload, Subject, User, UserCollection


class Client:
    """API request client"""

    types = {
        'wish': 1,
        'done': 2,
        'watch': 3,
        'stash': 4,
        'drop': 5,
    }

    subject_types = {
        'book': 1,
        'anime': 2,
        'music': 3,
        'game': 4,
        'real': 6,
    }

    def __init__(self):
        self.credential: Credential
        self.user: User

    def auth(self, code: str):
        """Auth with code and store credentials"""
        self.credential = get_access_token(code)
        store_token(self.credential)

    def refresh_token(self):
        """Refresh token if expired."""
        self._auth()
        new_credential = refresh_access_token(self.credential['refresh_token'])
        if new_credential is None:
            return False
        self.credential.update(new_credential)
        store_token(self.credential)
        return True

    def get_auth_status(self) -> None | str:
        """Return None if not authenticated, 'expired' if token expired, 'ok' if valid."""
        self._auth()
        status = get_token_status(self.credential['access_token'])
        if status is None:
            return 'expired'  # TODO: only an ad-hoc solution. Need to check the docs.
        expires: int = status['expires']
        if expires <= int(time.time()):
            logger.info('Token expired, refreshing...')
            return 'expired'
        return 'ok'

    def get_me(self) -> User:
        self._auth()
        me = get_me(self.credential['access_token'])
        self.user = me
        return me

    def get_collections(self, type: str = 'watch', subject_type: str = 'anime') -> list[UserCollection]:
        """
        Args: 
            type: wish, done, watch, stash, drop
            subject_type: book, anime, music, game, real
        """
        if not hasattr(self, 'user'):
            self.get_me()
        # subject_type: 2 for anime, type: 3 for watching
        collections = get_user_collections(token=self.credential['access_token'],
                                           username=self.user['username'],
                                           subject_type=self.subject_types[subject_type.lower()],
                                           type=self.types[type.lower()],
                                           limit=100)
        return collections['data']

    def get_subject(self, subject_id: int) -> Subject:
        """Return normal subject info"""
        # limit defines episodes to return I guess
        subject = get_subject(subject_id=subject_id, limit=100)
        return subject

    def watch_episode(self, episode_id: int):
        self._auth()
        put_user_episode(self.credential['access_token'], episode_id, watch=True)

    def watch_latest_episode(self, subject_id: int) -> Episode:
        """Watch the latest not watched episode."""
        self._auth()
        subject_eps = api.get_user_subject(self.credential['access_token'], subject_id, limit=200)
        ep = collection.episode_to_watch(subject_eps)
        if ep is not None:
            self.watch_episode(ep['id'])
            return ep
        raise Exception('No episode to watch')

    def get_user_collection(self, subject_id: int):
        if not hasattr(self, 'user'):
            self.get_me()
        return api.get_user_collection(self.credential['access_token'], self.user['username'], subject_id=subject_id)

    def add_collection(self,
                       subject_id: int,
                       rate: int | None = None,
                       comment: str | None = None,
                       tags: list[str] = [],
                       type: str = 'watch',
                       private: bool = False):
        """Only used for adding new collection."""
        self._auth()

        if not type.lower() in self.types:
            raise Exception(f'Invalid type: {type}. Choose one of: {self.types.keys()}')

        data: PostCollectionPayload = {
            'type': self.types[type.lower()],
            'rate': rate,
            'comment': comment,
            'tags': tags,
            'private': private,
        }
        api.post_collection(self.credential['access_token'], subject_id, data)
        return data

    def edit_collection(self,
                        subject_id: int,
                        type: str,
                        rate: int,
                        comment: str,
                        tags: list[str],
                        private: bool = False):
        """Types: 1: Wish, 2: Done, 3: Watch, 4: Stash, 5: Drop. 
        Case insensitive.
        """
        self._auth()

        if not type.lower() in self.types:
            raise Exception(f'Invalid type: {type}. Choose one of: {self.types.keys()}')

        data: PatchCollectionPayload = {
            'type': self.types[type.lower()],
            'rate': rate,
            'comment': comment,
            'tags': tags,
            'private': private,
        }
        api.patch_collection(self.credential['access_token'], subject_id, data)
        return data

    def list_anime(self, type: str) -> list[UserCollection]:
        """Types: 1: Wish, 2: Done, 3: Watch, 4: Stash, 5: Drop. 
        Case insensitive."""
        if not type.lower() in self.types:
            raise Exception(f'Invalid type: {type}. Choose one of: {self.types.keys()}')

        if not hasattr(self, 'user'):
            self.get_me()
        collections = api.get_user_collections(self.credential['access_token'],
                                               self.user['username'],
                                               subject_type=2,
                                               type=self.types[type.lower()],
                                               limit=100)
        return collections['data']

    def get_calendar(self):
        return api.get_calendar()

    def search(self,
               keyword: str | None,
               page: int = 1,
               subject_type: str = 'anime',
               tags: list[str] = [],
               rating: int = 6,
               rank: int = 2000):
        limit = 25
        offset = (page - 1) * limit
        types = [self.subject_types[subject_type.lower()]]

        return api.search(keyword,
                          'rank',
                          limit=limit,
                          offset=offset,
                          type=types,
                          tags=tags,
                          rating=(rating, 10),
                          rank=(1, rank))

    def _auth(self):
        if not hasattr(self, 'credential'):
            self.credential = load_token()
