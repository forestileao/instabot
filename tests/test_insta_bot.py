"""Unit tests for InstaBot's pure/testable logic.

These tests never hit the live Instagram API: all HTTP calls are mocked.
They target the specific bugs described in the "dasda" work order plan:

  * map_user_followers() must persist self.user_followers (not self.followers)
  * unfollow_non_followers() must respect the batch cap and skip mutual
    followers instead of resetting its counter every iteration.
"""
import json
import unittest
from unittest.mock import MagicMock

from insta_bot.src.insta_bot import InstaBot


def make_bot(verbose=False):
    bot = InstaBot(username='tester', password='secret')
    bot.verbose = verbose
    return bot


class MapUserFollowersTest(unittest.TestCase):
    def _fake_response(self, payload):
        response = MagicMock()
        response.content = json.dumps(payload).encode('utf-8')
        return response

    def test_saves_user_followers_when_limit_is_reached(self):
        bot = make_bot()
        bot.get_userid = MagicMock(return_value='123')

        first_page = {
            'status': 'ok',
            'data': {
                'user': {
                    'edge_followed_by': {
                        'count': 1,
                        'edges': [
                            {'node': {'username': 'alice', 'id': '1'}},
                        ],
                        'page_info': {'end_cursor': 'cursor-1'},
                    }
                }
            }
        }

        bot.session = MagicMock()
        bot.session.get.return_value = self._fake_response(first_page)

        with unittest.mock.patch('builtins.open', unittest.mock.mock_open()) as mocked_open, \
                unittest.mock.patch('json.dump') as mocked_dump:
            bot.map_user_followers(username='target', limit=1)

        # The bug fix: it must dump self.user_followers, not self.followers
        # (which is never set by this method and would raise AttributeError
        # in the old implementation).
        self.assertFalse(hasattr(bot, 'followers'))
        mocked_dump.assert_called_once()
        dumped_data, _ = mocked_dump.call_args[0]
        self.assertEqual(dumped_data, bot.user_followers)
        self.assertEqual(bot.user_followers, [{'username': 'alice', 'id': '1'}])

    def test_saves_partial_progress_on_fail_status(self):
        bot = make_bot()
        bot.get_userid = MagicMock(return_value='123')

        first_page = {
            'status': 'ok',
            'data': {
                'user': {
                    'edge_followed_by': {
                        'count': 5,
                        'edges': [
                            {'node': {'username': 'alice', 'id': '1'}},
                        ],
                        'page_info': {'end_cursor': 'cursor-1'},
                    }
                }
            }
        }
        failed_page = {'status': 'fail'}

        bot.session = MagicMock()
        bot.session.get.side_effect = [
            self._fake_response(first_page),
            self._fake_response(failed_page),
        ]

        with unittest.mock.patch('builtins.open', unittest.mock.mock_open()), \
                unittest.mock.patch('json.dump') as mocked_dump:
            bot.map_user_followers(username='target', limit=5)

        mocked_dump.assert_called_once()
        dumped_data, _ = mocked_dump.call_args[0]
        self.assertEqual(dumped_data, [{'username': 'alice', 'id': '1'}])


class UnfollowNonFollowersTest(unittest.TestCase):
    def test_skips_mutual_followers_and_respects_limit(self):
        bot = make_bot()
        bot.followers = [{'username': 'mutual', 'id': '1'}]
        bot.following = [
            {'username': 'mutual', 'id': '1'},
            {'username': 'stranger-1', 'id': '2'},
            {'username': 'stranger-2', 'id': '3'},
            {'username': 'stranger-3', 'id': '4'},
        ]
        bot.unfollow_user = MagicMock(return_value=True)

        unfollowed_count = bot.unfollow_non_followers(limit=2)

        self.assertEqual(unfollowed_count, 2)
        bot.unfollow_user.assert_any_call('2')
        bot.unfollow_user.assert_any_call('3')
        self.assertEqual(bot.unfollow_user.call_count, 2)

    def test_never_unfollows_current_followers(self):
        bot = make_bot()
        bot.followers = [
            {'username': 'a', 'id': '1'},
            {'username': 'b', 'id': '2'},
        ]
        bot.following = [
            {'username': 'a', 'id': '1'},
            {'username': 'b', 'id': '2'},
        ]
        bot.unfollow_user = MagicMock(return_value=True)

        unfollowed_count = bot.unfollow_non_followers(limit=50)

        self.assertEqual(unfollowed_count, 0)
        bot.unfollow_user.assert_not_called()


if __name__ == '__main__':
    unittest.main()
