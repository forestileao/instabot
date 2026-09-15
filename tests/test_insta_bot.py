"""Unit tests for insta_bot.src.insta_bot.InstaBot.

These tests never touch the network: every call that would normally hit
Instagram's servers is mocked out. They focus on the pieces of ``InstaBot``
that contain real logic (password encryption, response parsing, success /
failure handling) rather than on the HTTP plumbing itself.
"""
from unittest.mock import MagicMock, patch

import pytest

from insta_bot.src.insta_bot import InstaBot


@pytest.fixture
def bot():
    return InstaBot(username="alice", password="s3cr3t")


class TestGenerateEncryptedPassword:
    def test_contains_the_raw_password(self, bot):
        encrypted = bot.generate_encrypted_password()
        assert encrypted.endswith(":s3cr3t")

    def test_has_the_expected_prefix_and_format(self, bot):
        encrypted = bot.generate_encrypted_password()
        prefix, zero, timestamp, password = encrypted.split(":")
        assert prefix == "#PWD_INSTAGRAM_BROWSER"
        assert zero == "0"
        assert timestamp.isdigit()
        assert password == "s3cr3t"

    @patch("insta_bot.src.insta_bot.time.time", return_value=1234567890)
    def test_uses_the_current_time(self, _mock_time, bot):
        encrypted = bot.generate_encrypted_password()
        assert encrypted == "#PWD_INSTAGRAM_BROWSER:0:1234567890:s3cr3t"


class TestGetUserId:
    def test_returns_the_user_id_on_success(self, bot):
        response = MagicMock(status_code=200)
        response.content = b'{"graphql": {"user": {"id": "42"}}}'
        bot.session = MagicMock()
        bot.session.get.return_value = response

        assert bot.get_userid("john.doe") == "42"
        bot.session.get.assert_called_once_with(
            "https://instagram.com/john.doe/?__a=1"
        )

    def test_returns_none_when_request_fails(self, bot):
        response = MagicMock(status_code=404)
        bot.session = MagicMock()
        bot.session.get.return_value = response

        assert bot.get_userid("john.doe") is None


class TestLogin:
    def _make_response(self, content, cookies):
        response = MagicMock()
        response.content = content
        response.cookies = cookies
        return response

    def test_successful_login_sets_user_id(self, bot):
        home_response = self._make_response(b"", {"csrftoken": "csrf1"})
        login_content = b'{"authenticated": true, "userId": "123"}'
        login_response = self._make_response(login_content, {"csrftoken": "csrf2"})

        with patch("insta_bot.src.insta_bot.requests.Session") as MockSession:
            session = MockSession.return_value
            session.get.return_value = home_response
            session.post.return_value = login_response

            result = bot.login()

        assert result["authenticated"] is True
        assert bot.user_id == "123"

    def test_failed_login_does_not_set_user_id(self, bot):
        home_response = self._make_response(b"", {"csrftoken": "csrf1"})
        login_content = b'{"authenticated": false}'
        login_response = self._make_response(login_content, {"csrftoken": "csrf2"})

        with patch("insta_bot.src.insta_bot.requests.Session") as MockSession:
            session = MockSession.return_value
            session.get.return_value = home_response
            session.post.return_value = login_response

            result = bot.login()

        assert result["authenticated"] is False
        assert not hasattr(bot, "user_id")

    def test_connection_error_is_handled_gracefully(self, bot):
        with patch("insta_bot.src.insta_bot.requests.Session") as MockSession:
            session = MockSession.return_value
            session.get.side_effect = requests_connection_error()

            # Should not raise.
            result = bot.login()

        assert result is None


def requests_connection_error():
    import requests

    return requests.exceptions.ConnectionError()


class TestFollowUnfollowUser:
    def test_follow_user_returns_true_on_success(self, bot):
        response = MagicMock(status_code=200)
        response.content = b"ok"
        bot.session = MagicMock()
        bot.session.post.return_value = response

        assert bot.follow_user("99") is True
        bot.session.post.assert_called_once_with(
            "https://www.instagram.com/web/friendships/99/follow/"
        )

    def test_follow_user_returns_false_on_rate_limit_message(self, bot):
        response = MagicMock(status_code=200)
        response.content = "Please wait a few minutes".encode("utf-8")
        bot.session = MagicMock()
        bot.session.post.return_value = response

        assert bot.follow_user("99") is False

    def test_follow_user_returns_false_on_bad_status_code(self, bot):
        response = MagicMock(status_code=400)
        response.content = b"ok"
        bot.session = MagicMock()
        bot.session.post.return_value = response

        assert bot.follow_user("99") is False

    def test_unfollow_user_returns_true_on_success(self, bot):
        response = MagicMock(status_code=200)
        response.content = b"ok"
        bot.session = MagicMock()
        bot.session.post.return_value = response

        assert bot.unfollow_user("99") is True
        bot.session.post.assert_called_once_with(
            "https://www.instagram.com/web/friendships/99/unfollow/"
        )

    def test_unfollow_user_returns_false_on_rate_limit_message(self, bot):
        response = MagicMock(status_code=200)
        response.content = "Please wait a few minutes".encode("utf-8")
        bot.session = MagicMock()
        bot.session.post.return_value = response

        assert bot.unfollow_user("99") is False


class TestGetSuggestedFollowers:
    def test_parses_suggested_users_and_skips_instagram_accounts(self, bot):
        payload = {
            "status": "ok",
            "data": {
                "user": {
                    "edge_suggested_users": {
                        "edges": [
                            {
                                "node": {
                                    "description": "Instagram suggested",
                                    "user": {"username": "insta_acc", "id": "1"},
                                }
                            },
                            {
                                "node": {
                                    "description": "Real person",
                                    "user": {"username": "jane", "id": "2"},
                                }
                            },
                        ]
                    }
                }
            },
        }
        import json

        response = MagicMock(status_code=200)
        response.content = json.dumps(payload).encode("utf-8")
        bot.session = MagicMock()
        bot.session.get.return_value = response

        result = bot.get_suggested_followers()

        assert result == [{"username": "jane", "id": "2"}]

    def test_returns_none_when_request_fails(self, bot):
        response = MagicMock(status_code=500)
        bot.session = MagicMock()
        bot.session.get.return_value = response

        assert bot.get_suggested_followers() is None
