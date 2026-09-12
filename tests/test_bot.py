from unittest.mock import MagicMock

from insta_bot import config
from insta_bot.bot import InstaBot


def make_bot(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'CACHE_DIR', str(tmp_path))
    bot = InstaBot(username='user', password='pass')
    bot.client = MagicMock()
    bot.mapper = MagicMock()
    return bot


def test_get_follow_candidates_uses_suggested_when_no_target(monkeypatch, tmp_path):
    bot = make_bot(monkeypatch, tmp_path)
    bot.target_username = ''
    bot.mapper.suggested.return_value = [{'username': 'a', 'id': '1'}]

    candidates = bot._get_follow_candidates()

    assert candidates == [{'username': 'a', 'id': '1'}]
    bot.mapper.suggested.assert_called_once()


def test_get_follow_candidates_uses_target_followers_when_target_set(monkeypatch, tmp_path):
    bot = make_bot(monkeypatch, tmp_path)
    bot.target_username = 'someone'
    bot.client.get_user_id.return_value = 'target-id'
    bot.mapper.followers.return_value = [{'username': 'b', 'id': '2'}]

    candidates = bot._get_follow_candidates()

    assert candidates == [{'username': 'b', 'id': '2'}]
    bot.mapper.followers.assert_called_once_with('target-id', verbose=False)


def test_follow_batch_stops_once_hoped_followers_reached(monkeypatch, tmp_path):
    bot = make_bot(monkeypatch, tmp_path)
    bot.hoped_followers = 2
    bot.mapper.suggested.return_value = [
        {'username': 'a', 'id': '1'},
        {'username': 'b', 'id': '2'},
        {'username': 'c', 'id': '3'},
    ]
    bot.client.follow.return_value = True

    followed_count = bot._follow_batch(0)

    assert followed_count == 2
    assert bot.client.follow.call_count == 2


def test_follow_batch_waits_and_continues_when_rate_limited(monkeypatch, tmp_path):
    bot = make_bot(monkeypatch, tmp_path)
    bot.hoped_followers = 2
    bot.mapper.suggested.return_value = [
        {'username': 'a', 'id': '1'},
        {'username': 'b', 'id': '2'},
    ]
    bot.client.follow.side_effect = [False, True]
    sleep_mock = MagicMock()
    monkeypatch.setattr('insta_bot.bot.time.sleep', sleep_mock)

    followed_count = bot._follow_batch(0)

    assert followed_count == 1
    sleep_mock.assert_called_once_with(config.FOLLOW_RETRY_DELAY_SECONDS)


def test_unfollow_once_only_unfollows_accounts_not_following_back(monkeypatch, tmp_path):
    bot = make_bot(monkeypatch, tmp_path)
    bot.mapper.followers.return_value = [{'username': 'mutual', 'id': '1'}]
    bot.mapper.following.return_value = [
        {'username': 'mutual', 'id': '1'},
        {'username': 'stranger', 'id': '2'},
    ]
    bot.client.unfollow.return_value = True

    followers_count, following_count = bot._unfollow_once()

    assert (followers_count, following_count) == (1, 2)
    bot.client.unfollow.assert_called_once_with('2')


def test_unfollow_loop_stops_when_caught_up_and_not_forced(monkeypatch, tmp_path):
    bot = make_bot(monkeypatch, tmp_path)
    bot.unfollow_all_not_followers = False
    bot.mapper.followers.return_value = [{'username': 'a', 'id': '1'}]
    bot.mapper.following.return_value = [{'username': 'a', 'id': '1'}]

    bot._unfollow_loop()

    bot.mapper.followers.assert_called_once()
    bot.mapper.following.assert_called_once()
