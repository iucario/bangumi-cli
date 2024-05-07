import locale
from typing import Optional

import pick
import rich
import typer
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from bangumi_cli import settings
from bangumi_cli.api import NotFoundError
from bangumi_cli.auth import load_token, wait_user_input
from bangumi_cli.client import Client
from bangumi_cli.types import Subject, UserCollection

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

app = typer.Typer(no_args_is_help=True)


def print_warning(e):
    rich.print(f'[yellow]{e}[/yellow]')


def print_error(e: Exception, msg: str = ''):
    rich.print(f'[red]{e}[/red]')
    if msg:
        rich.print(f'{msg}')


def print_success(msg: str):
    rich.print(f'[green]{msg}[/green]')


def print_subject(subject: Subject):
    name = subject['name_cn'] or subject['name']
    summary = subject['summary']
    watching = subject['collection']['doing']
    date = subject['date']
    total_eps = subject['eps']
    tags = subject['tags']
    rating = subject.get('rating', {'score': -1, 'total': -1, 'rank': -1})
    score = rating['score']
    voters = rating['total']
    rank = rating['rank']

    console = Console()

    text = Text()
    text.append(f'ID: {subject["id"]}\n', style='blue')
    text.append(f'{name}\n', style='bold green')
    text.append(f'{date} Episodes: {total_eps} Viewers: {watching}\n')
    text.append(f'Score: {score} Rank: {rank} Voters: {voters}\n')
    text.append('Tags: \n', style='bold')
    text.append(f'{" ".join([t["name"] for t in tags])}\n', style='bright_black')
    text.append(f'\n{summary}')
    renderables = [Panel(text, box=box.ROUNDED)]
    console.print(Columns(renderables))


def subject_panel(calendar_item) -> Panel:
    """Return subject panel in simple format with less information"""
    name = calendar_item['name_cn'] or calendar_item['name']
    watching = calendar_item.get('collection', {}).get('doing', 0)
    date = calendar_item['air_date']
    rating = calendar_item.get('rating', {})
    score = rating.get('score', 'N/A')
    voters = rating.get('total', 0)
    rank = calendar_item.get('rank', 'N/A')

    text = Text()
    text.append(f'ID: {calendar_item["id"]}\n', style='blue')
    text.append(f'{name}\n', style='bold green')
    text.append(f'{date}\nViewers: {watching}\n')
    text.append(f'Score: {score} Rank: {rank} Voters: {voters}')

    panel = Panel(text, box=box.ROUNDED, width=38, padding=(0, 0))
    return panel


def verify_auth_code(code: str) -> Client:
    """Verify the user input code is correct. Returns a client with access token."""
    client = Client()
    try:
        client.auth(code)
        client.get_me()
        return client
    except Exception as e:
        print_error(e, 'Access token is wrong')
        raise typer.Exit(1)


def validate_auth_config() -> Client | None:
    """Check config in ~/.bangumi/auth.yaml exists and is valid. Refresh token if expired."""
    try:
        credential = load_token()
    except:
        return None
    client = Client()
    client.credential = credential
    token_status = client.get_auth_status()
    if token_status == 'expired':
        client.refresh_token()
    return client


def get_client() -> Client:
    """Get client from config or prompt user to login"""
    client = validate_auth_config()
    if client is None:
        print_warning('Login required')
        client = login()
    return client


def validate_collection_type(status: str):
    valid_items = ['watch', 'done', 'wish', 'drop', 'stash']
    if status.lower() not in valid_items:
        raise typer.BadParameter(f'"{status}". Choose one of {valid_items}')
    return status.lower()


def validate_subject_type(subject_type: str):
    valid_items = ['anime', 'book', 'game', 'music', 'real']
    if subject_type.lower() not in valid_items:
        raise typer.BadParameter(f'"{subject_type}". Choose one of {valid_items}')
    return subject_type.lower()


def validate_score_range(score: tuple[int, int]) -> tuple[int, int]:
    """Validate score range input"""

    def _validate_score(x: int):
        """Min: 0, max: 10"""
        return min(max(x, 0), 10)

    a, b = [_validate_score(x) for x in score]
    if a > b:
        return b, a
    return a, b


def collection_type_complete_list(incomplete: str):
    valid_items = [('watch', '在看'), ('done', '看过'), ('wish', '想看'), ('drop', '抛弃'), ('stash', '搁置')]
    for name, help_text in valid_items:
        if name.startswith(incomplete):
            yield (name, help_text)


def subject_type_complete_list(incomplete: str):
    valid_items = [('anime', '动画'), ('book', '书籍'), ('game', '游戏'), ('music', '音乐'), ('real', '三次元')]
    for name, help_text in valid_items:
        if name.startswith(incomplete):
            yield (name, help_text)


def prompt_collection_options(client: Client, collection: UserCollection):
    """Prompt to bookmark subject"""
    sub = collection['subject']
    eps = collection['ep_status']
    total = sub['eps']
    latest_ep = min(total, eps + 1)
    mark_ep = f'ep.{latest_ep}'
    options = [mark_ep, 'done', 'drop', 'stash', 'wish', 'watch']
    choice = Prompt.ask('Choose an action', default=mark_ep, choices=options)

    if choice == mark_ep:
        try:
            ep = client.watch_latest_episode(collection['subject_id'])
            print(f'Watched {ep["id"]}')
        except Exception as e:
            rich.print(f'[yellow]{e}[/yellow]')
            raise typer.Exit(1)
    else:
        prompt_edit_collection(client, sub, choice)  # type: ignore


def prompt_add_collection(client: Client, sub: Subject):
    """Add collection and set status to watch."""
    name = sub['name_cn'] or sub['name']
    action = 'watch'
    confirm = typer.confirm(f'{action.capitalize()} {name}?', default=True)
    if not confirm:
        rich.print('[yellow]Cancelled[/yellow]')
        return
    try:
        res = client.add_collection(subject_id=sub['id'], type='watch')
        print(f'Added {name} to watch')
    except Exception as e:
        print_warning(e)
        raise typer.Exit(1)


def prompt_edit_collection(client: Client, sub, action: str):
    """Actions: 'Done', 'Drop', 'Stash', 'Wish', 'Watch'"""
    status = client.get_user_collection(sub['id'])
    rate = Prompt.ask('Rate (1-10)', default=status['rate'], choices=list(map(str, range(1, 11))), show_default=True)
    tags_str = Prompt.ask('Tags (separate by space)', default=' '.join(status['tags']), show_default=True)
    tags = tags_str.split()
    comment = Prompt.ask('Comment', default=status['comment'], show_default=True)
    private = typer.confirm('Private', default=status['private'], show_default=True)

    data = {
        'type': action,
        'rate': int(rate),
        'tags': tags,
        'comment': comment,
        'private': private,
    }

    return confirm_edit_collection(client, sub, action, data)


def confirm_edit_collection(client: Client, sub: Subject, action: str, data: dict):
    """Only difference from the API is type is a string defining the action"""
    name = sub['name_cn'] or sub['name']
    rich.print(data)
    confirm = typer.confirm(f'{action.capitalize()} {name}?', default=True)
    if not confirm:
        rich.print('[yellow]Cancelled[/yellow]')
        return
    try:
        res = client.edit_collection(sub['id'], **data)
        print(f'Marked {action.lower()}')
    except Exception as e:
        print_warning(e)
        raise typer.Exit(1)


def prompt_latest_episode(client: Client) -> int:
    """Prompt to watch the latest episode"""
    collections = client.list_anime('watch')
    if not collections:
        print_warning('No collections to watch')
        raise typer.Exit(1)
    options = []
    for collection in collections:
        sub = collection['subject']
        eps = collection['ep_status']
        total = sub['eps']
        options.append(f'[{eps}/{total}] {sub["name_cn"]} ({sub["name"]})')
    title = 'Watch latest episode of subject'
    choice = pick.pick(options, title, indicator='>', default_index=0)
    index: int = choice[1]  # type: ignore
    subject_id = collections[index]['subject_id']
    return subject_id


"""Commands for bangumi-cli"""


@app.command(name='login', help='Authenticate in the browser and login')
def login() -> Client:
    client = validate_auth_config()
    if client is not None:
        rich.print('[green]Already logged in[/green]')
        return client
    code = wait_user_input()
    client = verify_auth_code(code)
    return client


@app.command(name='me', help='User info')
def me():
    client = get_client()
    me = client.get_me()
    name_or_id = me['username'] or me['id']
    url = f'https://bgm.tv/user/{name_or_id}'
    rich.print(f'Logged in as [green]{me["nickname"]}[/green]')
    rich.print(url)
    print()


# TODO: add more options
@app.command(name='list', help='List anime collections. [list|ls|l]')
@app.command(name='ls', hidden=True)
@app.command(name='l', hidden=True)
def list_anime(status: str = typer.Argument('watch',
                                            autocompletion=collection_type_complete_list,
                                            callback=validate_collection_type)):
    client = get_client()
    collections = client.list_anime(status)
    print()
    console = Console(highlight=False)
    table = Table(show_header=False, show_lines=False, box=box.SIMPLE, title=f'{status.capitalize()}')
    table.add_column('ID', style='blue')
    table.add_column('Status', style='cyan')
    table.add_column('Name')
    for collection in collections:
        sub = collection['subject']
        eps = collection['ep_status']
        sub_id = str(sub['id']).ljust(6)
        total = sub['eps']
        name = sub['name_cn'] or sub['name']
        ep_info = f'{eps}/{total} eps'
        table.add_row(sub_id, ep_info, name)
    console.print(table)
    print()


@app.command(name='mark', help='Watch the next episode. [mark|m]')
@app.command(name='m', hidden=True)
def watch_latest_episode(subject_id: Optional[int] = typer.Argument(None, help='Subject ID')):
    client = get_client()
    if subject_id is None:
        subject_id = prompt_latest_episode(client)
    ep = client.watch_latest_episode(subject_id)
    name = ep['name_cn'] or ep['name']
    print_success(f'Watched episode {ep["ep"]}.{name}')


@app.command(name='edit', help="Edit collection. [edit|e]")
@app.command(name='e', hidden=True)
def mark(subject_id: Optional[int] = typer.Argument(None, help='Subject ID'),
         collection_type: str = typer.Option('watch',
                                             '-s',
                                             '--status',
                                             help='Collection type',
                                             autocompletion=collection_type_complete_list,
                                             callback=validate_collection_type)):
    """Edit subject by id if provided, otherwise prompt to choose from list."""
    client = get_client()

    if subject_id is not None:
        collection = client.get_user_collection(subject_id)
        prompt_collection_options(client, collection)
    else:
        collections = client.get_collections(type=collection_type)
        if not collections:
            print_warning(f'No collections of type {collection_type}')
            raise typer.Exit(1)

        options = []
        for collection in collections:
            sub = collection['subject']
            eps = collection['ep_status']
            total = sub['eps']
            options.append(f'[{eps}/{total}] {sub["name_cn"]} ({sub["name"]})')
        title = 'Bookmark subject'
        choice = pick.pick(options, title, indicator='>', default_index=0)
        collection: UserCollection = collections[choice[1]]  # type: ignore
        prompt_collection_options(client, collection)


@app.command(name='add', help='Add collection to your list')
def add_collection(sub_id: int = typer.Argument(..., help='Subject ID')):
    """If subject already collected, edit it to `watch` status. Otherwise add it. 
    Don't get it wrong because user editted information will lost.
    """
    client = get_client()
    sub = client.get_subject(sub_id)
    try:
        collection = client.get_user_collection(sub_id)
    except NotFoundError:
        prompt_add_collection(client, sub)
    else:
        prompt_edit_collection(client, sub, 'watch')


@app.command(name='cal', help='Calendar')
def calendar():
    print()
    client = Client()
    cal = client.get_calendar()
    cal.sort(key=lambda x: x['weekday']['id'])
    console = Console(highlight=False)
    with console.pager(styles=True):
        for day in cal:
            console.print(f'[bold][yellow]{day["weekday"]["cn"]}[/yellow][/bold]')
            columns = Columns([subject_panel(item) for item in day['items']])
            console.print(columns)


@app.command(name='search', help='Search anime. [search|s]')
@app.command(name='s', hidden=True)
def search(keywords: Optional[list[str]] = typer.Argument(None, help='Keywords'),
           page: int = typer.Option(1, '-p', '--page', help='Page number'),
           subject_type: str = typer.Option('anime',
                                            '-t',
                                            '--type',
                                            autocompletion=subject_type_complete_list,
                                            callback=validate_subject_type,
                                            help='Subject type'),
           tags: list[str] = typer.Option(
               [],
               '-g',
               '--tag',
               help='Tags',
               case_sensitive=False,
           ),
           score: int = typer.Option(5, '-s', '--score', help='Minimum score'),
           rank: int = typer.Option(2000, '-r', '--rank', help='Maximum rank')):
    print()
    client = Client()
    search_str = ' '.join(keywords) if keywords is not None else None
    results = client.search(search_str, page=page, subject_type=subject_type, tags=tags, rating=score, rank=rank)
    title = f'Search results for "{search_str}" tags: {tags}'
    table = Table(title=title, box=box.MINIMAL)
    table.add_column('ID', style='cyan')
    table.add_column('Name', style='green', no_wrap=True)
    table.add_column('Date')
    table.add_column('Score')
    table.add_column('Rank')
    for result in results:
        name = result['name_cn'] if result['name_cn'] else result['name']
        table.add_row(str(result['id']), name, result['date'], str(result['score']), str(result['rank']))
    console = Console(highlight=False)
    with console.pager(styles=True):
        console.print(table)


@app.command(name='info', help='Subject info. [info|i]')
@app.command(name='i', hidden=True)
def subject_info(sub_id: int = typer.Argument(..., help='Subject ID')):
    client = Client()
    sub = client.get_subject(sub_id)
    print_subject(sub)


def version(flag: bool):
    if flag:
        rich.print(f'bgm-cli [green]{settings.version}[/green]')
        raise typer.Exit()


@app.callback()
def main(ctx: typer.Context, verison: bool = typer.Option(False, '--version', '-v', callback=version)):
    pass


if __name__ == '__main__':
    app()
