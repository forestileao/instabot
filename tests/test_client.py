from unittest.mock import MagicMock

import pytest
import requests

from insta_bot.client import InstagramClient, InstagramClientError


def make_client():
    return InstagramClient(username='user', password='pass')


def test_login_success_sets_user_id():
    client = make_client()
    client.session = MagicMock()
    client.session.get.return_value = MagicMock(cookies={'csrftoken': 'abc'})
    client.session.post.return_value = MagicMock(
        cookies={'csrftoken': 'def'},
        json=lambda: {'authenticated': True, 'userId': '42'},
    )

    payload = client.login()

    assert payload['userId'] == '42'
    assert client.user_id == '42'


def test_login_raises_when_not_authenticated():
    client = make_client()
    client.session = MagicMock()
    client.session.get.return_value = MagicMock(cookies={'csrftoken': 'abc'})
    client.session.post.return_value = MagicMock(
        cookies={'csrftoken': 'def'},
        json=lambda: {'authenticated': False},
    )

    with pytest.raises(InstagramClientError):
        client.login()


def test_login_raises_on_connection_error():
    client = make_client()
    client.session = MagicMock()
    client.session.get.side_effect = requests.exceptions.ConnectionError()

    with pytest.raises(InstagramClientError):
        client.login()


def test_get_user_id_returns_id_on_success():
    client = make_client()
    client.session = MagicMock()
    client.session.get.return_value = MagicMock(
        status_code=200,
        json=lambda: {'graphql': {'user': {'id': '123'}}},
    )

    assert client.get_user_id('someone') == '123'


def test_get_user_id_returns_none_on_failure_status():
    client = make_client()
    client.session = MagicMock()
    client.session.get.return_value = MagicMock(status_code=404)

    assert client.get_user_id('someone') is None


def test_follow_returns_true_on_success():
    client = make_client()
    client.session = MagicMock()
    client.session.post.return_value = MagicMock(status_code=200, text='ok')

    assert client.follow('123') is True


def test_follow_returns_false_when_rate_limited_message():
    client = make_client()
    client.session = MagicMock()
    client.session.post.return_value = MagicMock(status_code=200, text='Please wait a few minutes')

    assert client.follow('123') is False


def test_unfollow_returns_false_on_bad_status():
    client = make_client()
    client.session = MagicMock()
    client.session.post.return_value = MagicMock(status_code=400, text='')

    assert client.unfollow('123') is False
