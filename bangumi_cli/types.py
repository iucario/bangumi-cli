from dataclasses import dataclass
from typing import TypedDict


class User(TypedDict):
    avatar: dict
    id: int
    nickname: str
    username: str
    sign: str
    user_group: int


class ErrorDetail(TypedDict):
    title: str
    description: str
    detail: str


class Tag(TypedDict):
    name: str
    count: int


class Subject(TypedDict):
    date: str
    images: dict
    name: str
    name_cn: str
    short_summary: str
    summary: str
    tags: list[Tag]
    score: float
    type: int  # 2: anime
    id: int
    eps: int
    volumes: int
    collection_total: int
    rank: int
    rating: dict  # { total:int, count: {score: int} }
    collection: dict  # { watching: int, on_hold: int, ... }


class UserCollection(TypedDict):
    """My collection item"""
    updated_at: str
    comment: str
    tags: list[str]  # my tags
    subject: Subject
    subject_id: int
    vol_status: int
    ep_status: int  # current episode?
    subject_type: int  # 2: anime
    type: int  # 3: watching
    rate: int
    private: bool


class UserCollections(TypedDict):
    total: int
    limit: int
    offset: int
    data: list[UserCollection]


class Episode(TypedDict):
    airdate: str
    name: str
    name_cn: str
    duration: str
    desc: str
    ep: int
    sort: int
    id: int
    subject_id: int
    comment: int
    type: int  # 0: normal episode 1: special episode
    disc: int
    duration_seconds: int


class UserEpisode(TypedDict):
    episode: Episode
    type: int  # 0: not watched 2: watched


class UserEpisodes(TypedDict):
    total: int
    limit: int
    offset: int
    data: list[UserEpisode]


class Calendar(TypedDict):
    weekday: dict  # {en: Mon, id: 1, ...}
    items: list[Subject]


@dataclass
class SearchFilter:
    type: list[int]
    tag: list[str]
    air_date: list[str]  # [">=2020-07-01", "<2020-10-01"]
    rating: list[str]  # [">=6", "<=10"]
    rank: list[str]  # [">=1", "<=2000"]
    nsfw: str = ''  # use "include" to allow nsfw results


@dataclass
class SearchPayload:
    filter: SearchFilter
    keyword: str = ""
    sort: str = "rank"
    limit: int = 10
    offset: int = 0


class SearchResult(TypedDict):
    data: list[Subject]
    total: int
    limit: int
    offset: int


class PatchCollectionPayload(TypedDict):
    type: int  #
    rate: int
    comment: str
    private: bool
    tags: list[str]


class PostCollectionPayload(TypedDict):
    type: int  #
    rate: int | None
    comment: str | None
    private: bool
    tags: list[str]
