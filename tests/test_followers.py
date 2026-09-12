from insta_bot import config
from insta_bot.followers import FollowerMapper


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get_json(self, path, params=None):
        self.calls.append(params)
        return self.pages.pop(0)


def make_edge(usernames, has_next_page, end_cursor='cursor'):
    return {
        'edges': [{'node': {'username': name, 'id': f'id-{name}'}} for name in usernames],
        'page_info': {'has_next_page': has_next_page, 'end_cursor': end_cursor},
    }


def test_followers_paginates_until_no_next_page():
    pages = [
        {'data': {'user': {'edge_followed_by': make_edge(['a', 'b'], has_next_page=True)}}},
        {'data': {'user': {'edge_followed_by': make_edge(['c'], has_next_page=False)}}},
    ]
    client = FakeClient(pages)
    mapper = FollowerMapper(client)

    result = mapper.followers('user-1')

    assert [u['username'] for u in result] == ['a', 'b', 'c']
    assert len(client.calls) == 2


def test_followers_stops_when_limit_reached():
    pages = [
        {'data': {'user': {'edge_followed_by': make_edge(['a', 'b', 'c'], has_next_page=True)}}},
    ]
    client = FakeClient(pages)
    mapper = FollowerMapper(client)

    result = mapper.followers('user-1', limit=2)

    assert [u['username'] for u in result] == ['a', 'b']


def test_followers_stops_on_fail_status():
    pages = [{'status': 'fail'}]
    client = FakeClient(pages)
    mapper = FollowerMapper(client)

    assert mapper.followers('user-1') == []


def test_following_uses_edge_follow_key():
    pages = [
        {'data': {'user': {'edge_follow': make_edge(['x'], has_next_page=False)}}},
    ]
    client = FakeClient(pages)
    mapper = FollowerMapper(client)

    result = mapper.following('user-1')

    assert [u['username'] for u in result] == ['x']


def test_first_page_request_has_no_after_param_and_fetches_mutual():
    pages = [
        {'data': {'user': {'edge_followed_by': make_edge([], has_next_page=False)}}},
    ]
    client = FakeClient(pages)
    mapper = FollowerMapper(client)

    mapper.followers('user-1')

    first_call_variables = client.calls[0]
    assert first_call_variables['query_hash'] == config.FOLLOWERS_QUERY_HASH
    assert '"fetch_mutual": true' in first_call_variables['variables']
    assert 'after' not in first_call_variables['variables']


def test_suggested_filters_out_instagram_promotional_entries():
    client = FakeClient([
        {
            'data': {
                'user': {
                    'edge_suggested_users': {
                        'edges': [
                            {'node': {'description': 'Instagram', 'user': {'username': 'ig', 'id': '1'}}},
                            {'node': {'description': 'Popular', 'user': {'username': 'real', 'id': '2'}}},
                        ]
                    }
                }
            }
        }
    ])
    mapper = FollowerMapper(client)

    result = mapper.suggested()

    assert result == [{'username': 'real', 'id': '2'}]
