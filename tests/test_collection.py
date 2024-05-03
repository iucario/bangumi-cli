import json

from bangumi_cli.types import Episode, UserEpisode, UserEpisodes
from bangumi_cli.collection import episode_to_unwatch, episode_to_watch, sort_episodes


def test_episode_to_unwatch():
    with open('example_data/328609.json') as f:
        subject: UserEpisodes = json.load(f)
    episode = episode_to_unwatch(subject)
    assert episode is not None
    assert episode['id'] == 1128648


def test_episode_to_watch():
    with open('example_data/328609.json') as f:
        subject: UserEpisodes = json.load(f)
    episode = episode_to_watch(subject)
    assert episode is not None
    assert episode['id'] == 1128649