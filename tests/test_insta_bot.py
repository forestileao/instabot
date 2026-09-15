"""Unit tests for insta_bot.src.insta_bot.InstaBot.

These tests avoid any real network access. All HTTP interactions are
performed through ``self.session`` (a ``requests.Session`` instance), so
we replace it with a ``unittest.mock.MagicMock`` and assert on how the
bot uses it.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from insta_bot.src.insta_bot import InstaBot


@pytest.fixture
def bot():
    return InstaBot(username="john.doe", password="s3cr3t")


def _response(status_code=200, content=b"", cookies=None):
    """Build a lightweight stand-in for a ``requests.Response``."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.cookies = cookies or {}
    return resp


class TestGenerateEncryptedPassword:
    def test_matches_instagram_expected_format(self, bot):
        with patch("insta_bot.src.insta_bot.time.time", return_value=1700000000):
            result = bot.generate_encrypted_password()

        assert result == "#PWD_INSTAGRAM_BROWSER:0:1700000000:s3cr3t"

    def test_embeds_the_current_password(self, bot):
        bot.password = "another-pass"
        with patch("insta_bot.src.insta_bot.time.time", return_value=1):
            result = bot.generate_encrypted_password()

        assert result.endswith(":another-pass")


class TestGetUserId:
    def test_returns_id_when_request_succeeds(self, bot):
        payload = json.dumps({"graphql": {"user": {"id": "42"}}}).encode("utf-8")
        bot.session = MagicMock()
        bot.session.get.return_value = _response(status_code=200, content=payload)

        user_id = bot.get_userid("john.doe")

        assert user_id == "42"
        bot.session.get.assert_called_once_with(
            "https://instagram.com/john.doe/?__a=1"
        )

    def test_returns_none_when_request_fails(self, bot):
        bot.session = MagicMock()
        bot.session.get.return_value = _response(status_code=404)

        assert bot.get_userid("john.doe") is None


class TestLogin:
    def test_sets_user_id_when_authenticated(self, bot):
        get_response = _response(cookies={"csrftoken": "get-token"})
        post_content = json.dumps({"authenticated": True, "userId": "99"}).encode(
            "utf-8"
        )
        post_response = _response(
            content=post_content, cookies={"csrftoken": "post-token"}
        )

        mock_session = MagicMock()
        mock_session.get.return_value = get_response
        mock_session.post.return_value = post_response

        with patch(
            "insta_bot.src.insta_bot.requests.Session", return_value=mock_session
        ):
            result = bot.login()

        assert bot.user_id == "99"
        assert result == {"authenticated": True, "userId": "99"}
        mock_session.post.assert_called_once_with(
            "https://www.instagram.com/accounts/login/ajax/",
            data={
                "username": "john.doe",
                "enc_password": bot.generate_encrypted_password(),
            },
            allow_redirects=True,
        )

    def test_does_not_set_user_id_when_not_authenticated(self, bot):
        get_response = _response(cookies={"csrftoken": "get-token"})
        post_content = json.dumps({"authenticated": False}).encode("utf-8")
        post_response = _response(
            content=post_content, cookies={"csrftoken": "post-token"}
        )

        mock_session = MagicMock()
        mock_session.get.return_value = get_response
        mock_session.post.return_value = post_response

        with patch(
            "insta_bot.src.insta_bot.requests.Session", return_value=mock_session
        ):
            bot.login()

        assert not hasattr(bot, "user_id")

    def test_returns_none_on_connection_error(self, bot):
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError()

        with patch(
            "insta_bot.src.insta_bot.requests.Session", return_value=mock_session
        ):
            result = bot.login()

        assert result is None


class TestFollowUser:
    def test_returns_true_on_success(self, bot):
        bot.session = MagicMock()
        bot.session.post.return_value = _response(
            status_code=200, content=b'{"ok":true}'
        )

        assert bot.follow_user("321") is True
        bot.session.post.assert_called_once_with(
            "https://www.instagram.com/web/friendships/321/follow/"
        )

    def test_returns_false_when_rate_limited(self, bot):
        bot.session = MagicMock()
        bot.session.post.return_value = _response(
            status_code=200, content=b"Please wait a few minutes"
        )

        assert bot.follow_user("321") is False

    def test_returns_false_on_non_200_status(self, bot):
        bot.session = MagicMock()
        bot.session.post.return_value = _response(status_code=400, content=b"{}")

        assert bot.follow_user("321") is False


class TestUnfollowUser:
    def test_returns_true_on_success(self, bot):
        bot.session = MagicMock()
        bot.session.post.return_value = _response(
            status_code=200, content=b'{"ok":true}'
        )

        assert bot.unfollow_user("321") is True
        bot.session.post.assert_called_once_with(
            "https://www.instagram.com/web/friendships/321/unfollow/"
        )

    def test_returns_false_when_rate_limited(self, bot):
        bot.session = MagicMock()
        bot.session.post.return_value = _response(
            status_code=200, content=b"Please wait a few minutes"
        )

        assert bot.unfollow_user("321") is False


class TestGetSuggestedFollowers:
    def test_filters_out_instagram_own_suggestions(self, bot):
        payload = {
            "status": "ok",
            "data": {
                "user": {
                    "edge_suggested_users": {
                        "edges": [
                            {
                                "node": {
                                    "description": "Instagram suggested",
                                    "user": {"username": "spam", "id": "1"},
                                }
                            },
                            {
                                "node": {
                                    "description": "Friend of friend",
                                    "user": {"username": "real.person", "id": "2"},
                                }
                            },
                        ]
                    }
                }
            }
        }
        bot.session = MagicMock()
        bot.session.get.return_value = _response(
            status_code=200, content=json.dumps(payload).encode("utf-8")
        )

        result = bot.get_suggested_followers()

        assert result == [{"username": "real.person", "id": "2"}]

    def test_returns_none_when_request_fails(self, bot):
        bot.session = MagicMock()
        bot.session.get.return_value = _response(status_code=500)

        assert bot.get_suggested_followers() is None
