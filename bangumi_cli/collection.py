from bangumi_cli.types import Episode, UserEpisode, UserEpisodes


def compare(x: UserEpisode) -> int:
    """Sort by episode type and id. Episode.type=0 is normal episode"""
    return x['episode']['type'] * 10000 + x['episode']['sort']


def sort_episodes(episodes: list[UserEpisode]) -> list[UserEpisode]:
    episodes.sort(key=compare)
    return episodes


def filter_episodes(episodes: list[UserEpisode]) -> list[UserEpisode]:
    return [ep for ep in episodes if ep_type(ep) == 'normal']


def episode_to_watch(subject: UserEpisodes) -> Episode | None:
    """Sort normal episodes by id, then return the first episode that is not done"""
    episodes = sort_episodes(subject['data'])
    normal_episodes = [ep for ep in episodes if ep_type(ep) == 'normal']
    for ep in normal_episodes:
        if ep_status(ep['type']) != 'done':
            return ep['episode']
    return None


def episode_to_unwatch(subject: UserEpisodes) -> Episode | None:
    """Sort normal episodes by id, then return the last episode that is done"""
    episodes = sort_episodes(subject['data'])
    normal_episodes = [ep for ep in episodes if ep_type(ep) == 'normal']
    for ep in reversed(normal_episodes):
        if ep_status(ep['type']) == 'done':
            return ep['episode']
    return None


def ep_status(x: int | UserEpisode) -> str:
    """Returns episode type empty, todo, done or dropped"""
    status = {0: 'empty', 1: 'todo', 2: 'done', 3: 'dropped'}
    if isinstance(x, dict):
        return status[x['type']]
    elif isinstance(x, int):
        return status[x]
    else:
        raise TypeError(f'ep_status: {x} is not int or dict')


def ep_type(x: int | UserEpisode) -> str:
    """Episode.episode.type"""
    types = {
        0: 'normal',
        1: 'special',
        2: 'openning',
        3: 'ending',
    }
    if isinstance(x, dict):
        return types[x['episode']['type']]
    elif isinstance(x, int):
        return types[x]
    else:
        raise TypeError(f'ep_type: {x} is not int or dict')