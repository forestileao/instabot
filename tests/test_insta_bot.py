import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PACKAGE_DIR = Path(__file__).resolve().parents[1] / 'insta_bot'
sys.path.insert(0, str(PACKAGE_DIR))

from src.insta_bot import (  # noqa: E402
    FOLLOWERS_QUERY_HASH,
    FOLLOWING_QUERY_HASH,
    SUGGESTED_QUERY,
    SUGGESTED_QUERY_HASH,
    InstaBot,
)
import main  # noqa: E402


def _response(status_code=200, body='', cookies=None):
    response = Mock()
    response.status_code = status_code
    response.content = body.encode('utf-8') if isinstance(body, str) else body
    response.cookies = cookies or {}
    return response


def _edge(username, user_id, description=None, nested_user=False):
    node = {'username': username, 'id': user_id}
    if nested_user:
        node = {'description': description, 'user': {'username': username, 'id': user_id}}
    return {'node': node}


class InstaBotHelpersTest(unittest.TestCase):
    def setUp(self):
        self.bot = InstaBot('alice', 'secret')
        self.bot.session = Mock()

    def test_encrypted_password_uses_browser_prefix_and_unix_time(self):
        with patch('src.insta_bot.time.time', return_value=1600000000.9):
            password = self.bot.generate_encrypted_password()
        self.assertEqual(password, '#PWD_INSTAGRAM_BROWSER:0:1600000000:secret')

    def test_connection_url_matches_legacy_graphql_format(self):
        url = self.bot._connection_url(
            FOLLOWERS_QUERY_HASH, '99', first=24, fetch_mutual=True,
        )
        self.assertEqual(
            url,
            'https://www.instagram.com/graphql/query/?query_hash='
            'c76146de99bb02f6415203be841dd25a&variables='
            '{"id":"99","include_reel":true,"fetch_mutual":true,"first":24}',
        )

        paged = self.bot._connection_url(
            FOLLOWING_QUERY_HASH, '99', first=24, fetch_mutual=False, cursor='abc',
        )
        self.assertEqual(
            paged,
            'https://www.instagram.com/graphql/query/?query_hash='
            'd04b0a864b4b54837c0d870b0e77e076&variables='
            '{"id":"99","include_reel":true,"fetch_mutual":false,"first":24,"after":"abc"}',
        )

    def test_get_userid_returns_id_or_none(self):
        self.bot.session.get.return_value = _response(
            200, json.dumps({'graphql': {'user': {'id': '42'}}}),
        )
        self.assertEqual(self.bot.get_userid('bob'), '42')
        self.assertEqual(
            self.bot.session.get.call_args[0][0],
            'https://instagram.com/bob/?__a=1',
        )

        self.bot.session.get.return_value = _response(404, '{}')
        self.assertIsNone(self.bot.get_userid('missing'))

    def test_friendship_action_reports_status_and_rate_limit(self):
        self.bot.session.post.return_value = _response(200, 'ok')
        with patch('sys.stdout') as stdout:
            self.assertTrue(self.bot.follow_user('7'))
        stdout.write.assert_any_call('[200]')
        self.assertEqual(
            self.bot.session.post.call_args[0][0],
            'https://www.instagram.com/web/friendships/7/follow/',
        )

        self.bot.session.post.return_value = _response(200, 'Please wait')
        self.assertFalse(self.bot.unfollow_user('7'))
        self.bot.session.post.return_value = _response(429, 'nope')
        self.assertFalse(self.bot.follow_user('7'))

    def test_suggested_followers_skips_instagram_descriptions(self):
        payload = {
            'status': 'ok',
            'data': {
                'user': {
                    'edge_suggested_users': {
                        'edges': [
                            _edge('real', '1', description='Photographer', nested_user=True),
                            _edge('ig', '2', description='Instagram', nested_user=True),
                        ]
                    }
                }
            },
        }
        self.bot.session.get.return_value = _response(200, json.dumps(payload))
        suggested = self.bot.get_suggested_followers()
        self.assertEqual(suggested, [{'username': 'real', 'id': '1'}])
        requested = self.bot.session.get.call_args[0][0]
        self.assertIn(SUGGESTED_QUERY_HASH, requested)
        self.assertIn(json.dumps(SUGGESTED_QUERY), requested)

        self.bot.session.get.return_value = _response(500, '{}')
        self.assertIsNone(self.bot.get_suggested_followers())

    def test_login_stores_user_id_when_authenticated(self):
        home = _response(200, '', cookies={'csrftoken': 'home-token'})
        login = _response(
            200,
            json.dumps({'authenticated': True, 'userId': '55'}),
            cookies={'csrftoken': 'login-token'},
        )
        self.bot.session = Mock()
        created = Mock()
        created.get.return_value = home
        created.post.return_value = login
        created.headers = {}
        with patch('src.insta_bot.requests.Session', return_value=created), \
                patch('src.insta_bot.time.time', return_value=10):
            result = self.bot.login()
        self.assertEqual(result['userId'], '55')
        self.assertEqual(self.bot.user_id, '55')
        self.assertEqual(created.headers['user-agent'].split(' ')[0], 'Mozilla/5.0')
        self.assertEqual(created.headers['Referer'], 'https://www.instagram.com')
        self.assertEqual(created.headers['x-csrftoken'], 'login-token')
        posted = created.post.call_args
        self.assertEqual(posted.kwargs['data']['username'], 'alice')
        self.assertEqual(
            posted.kwargs['data']['enc_password'],
            '#PWD_INSTAGRAM_BROWSER:0:10:secret',
        )

    def test_login_prints_error_without_user_id(self):
        home = _response(200, '', cookies={'csrftoken': 't'})
        login = _response(200, json.dumps({'authenticated': False}), cookies={'csrftoken': 't'})
        created = Mock()
        created.get.return_value = home
        created.post.return_value = login
        created.headers = {}
        with patch('src.insta_bot.requests.Session', return_value=created):
            result = self.bot.login()
        self.assertFalse(result['authenticated'])
        self.assertFalse(hasattr(self.bot, 'user_id'))

    def test_login_connection_error_returns_none(self):
        import requests
        created = Mock()
        created.headers = {}
        created.get.side_effect = requests.exceptions.ConnectionError()
        with patch('src.insta_bot.requests.Session', return_value=created):
            self.assertIsNone(self.bot.login())

    def test_map_followers_writes_cache_when_count_matches(self):
        page = {
            'status': 'ok',
            'data': {
                'user': {
                    'edge_followed_by': {
                        'count': 1,
                        'page_info': {'end_cursor': 'c'},
                        'edges': [_edge('bob', '2')],
                    }
                }
            },
        }
        self.bot.user_id = '1'
        self.bot.verbose = True
        self.bot.session.get.return_value = _response(200, json.dumps(page))
        with patch('builtins.open', unittest.mock.mock_open()) as opened, \
                patch('src.insta_bot.json.dump') as dump:
            self.bot.map_followers()
        self.assertEqual(self.bot.followers, [{'username': 'bob', 'id': '2'}])
        self.assertEqual(self.bot.foll_num, 1)
        self.assertTrue(opened.call_args[0][0].endswith('/../cache/followers.json'))
        dump.assert_called_once()

    def test_map_user_followers_dumps_own_followers_list(self):
        page = {
            'status': 'ok',
            'data': {
                'user': {
                    'edge_followed_by': {
                        'count': 9,
                        'page_info': {'end_cursor': 'c'},
                        'edges': [_edge('targetfan', '8')],
                    }
                }
            },
        }
        self.bot.verbose = False
        self.bot.followers = [{'username': 'me', 'id': '1'}]
        self.bot.session.get.return_value = _response(200, json.dumps(page))
        self.bot.get_userid = Mock(return_value='77')
        with patch('builtins.open', unittest.mock.mock_open()), \
                patch('src.insta_bot.json.dump') as dump:
            self.bot.map_user_followers('target', limit=1)
        self.assertEqual(self.bot.user_followers, [{'username': 'targetfan', 'id': '8'}])
        dump.assert_called_once()
        self.assertEqual(dump.call_args[0][0], self.bot.followers)

    def test_map_stops_on_fail_without_cache_write(self):
        page = {
            'status': 'fail',
            'data': {'user': {'edge_follow': {'count': 3, 'edges': [], 'page_info': {}}}},
        }
        self.bot.user_id = '1'
        self.bot.verbose = False
        self.bot.session.get.return_value = _response(200, json.dumps(page))
        with patch('src.insta_bot.json.dump') as dump:
            self.bot.map_following()
        dump.assert_not_called()
        self.assertEqual(self.bot.following, [])
        self.assertEqual(self.bot.following_num, 3)

    def test_map_requires_verbose_from_start(self):
        self.bot.session.get.return_value = _response(200, '{}')
        with self.assertRaises(AttributeError):
            self.bot.map_followers()

    def test_just_follow_skips_when_snapshot_already_meets_goal(self):
        self.bot.other_user = False
        self.bot.hoped_foll = 5

        def map_followers():
            self.bot.foll_num = 5

        self.bot.map_followers = map_followers
        self.bot.get_suggested_followers = Mock(side_effect=AssertionError('should not follow'))
        self.bot.just_follow()
        self.bot.get_suggested_followers.assert_not_called()

    def test_unfollow_keeps_accounts_that_follow_back(self):
        self.bot.followers = [{'username': 'bob', 'id': '2'}]
        self.bot.following = [
            {'username': 'bob', 'id': '2'},
            {'username': 'cara', 'id': '3'},
        ]
        self.bot.unfollow_user = Mock(return_value=True)
        self.bot._unfollow_non_followers()
        self.bot.unfollow_user.assert_called_once_with('3')

    def test_start_sets_flags_and_starts_both_threads_after_failed_login(self):
        self.bot.login = Mock(return_value=None)
        with patch('src.insta_bot.Thread') as thread_cls:
            self.bot.start(target_username='', hoped_foll=10, unfollow_all_not_followers=False, verbose=True)
        self.assertFalse(self.bot.other_user)
        self.assertFalse(hasattr(self.bot, 'target_username'))
        self.assertEqual(self.bot.hoped_foll, 10)
        self.assertTrue(self.bot.verbose)
        self.assertFalse(self.bot.unfollow_all_not_followers)
        self.assertEqual(thread_cls.call_count, 2)
        self.assertEqual(thread_cls.return_value.start.call_count, 2)

        with patch('src.insta_bot.Thread'):
            self.bot.start(target_username='target')
        self.assertTrue(self.bot.other_user)
        self.assertEqual(self.bot.target_username, 'target')


class MainTest(unittest.TestCase):
    def test_load_credentials(self):
        with patch('builtins.open', unittest.mock.mock_open(read_data='{"username": "a", "password": "b", "target_username": ""}')):
            credentials = main.load_credentials()
        self.assertEqual(credentials['username'], 'a')
        self.assertEqual(credentials['target_username'], '')


if __name__ == '__main__':
    unittest.main()
