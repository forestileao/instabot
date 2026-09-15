"""Unit tests for insta_bot.src.insta_bot.InstaBot.

These tests avoid making any real network calls: every interaction with
``requests`` is mocked out so the suite can run offline and deterministically.
"""
import json
import unittest
from unittest.mock import MagicMock, patch

import requests

from insta_bot.src.insta_bot import InstaBot


def make_response(status_code=200, content="", cookies=None):
    """Build a lightweight stand-in for a requests.Response object."""
    response = MagicMock()
    response.status_code = status_code
    response.content = content.encode("utf-8")
    response.cookies = cookies or {}
    return response


class GenerateEncryptedPasswordTest(unittest.TestCase):
    def setUp(self):
        self.bot = InstaBot(username="alice", password="s3cret")

    def test_contains_expected_prefix_and_password(self):
        enc_password = self.bot.generate_encrypted_password()

        self.assertTrue(enc_password.startswith("#PWD_INSTAGRAM_BROWSER:0:"))
        self.assertTrue(enc_password.endswith(":s3cret"))

    def test_timestamp_segment_is_numeric(self):
        enc_password = self.bot.generate_encrypted_password()

        # Format: #PWD_INSTAGRAM_BROWSER:0:<timestamp>:<password>
        timestamp_segment = enc_password.split(":")[2]
        self.assertTrue(timestamp_segment.isdigit())


class LoginTest(unittest.TestCase):
    def setUp(self):
        self.bot = InstaBot(username="alice", password="s3cret")

    @patch("insta_bot.src.insta_bot.requests.Session")
    def test_successful_login_sets_user_id(self, session_cls):
        session = session_cls.return_value
        session.get.return_value = make_response(
            cookies={"csrftoken": "abc123"}
        )
        session.post.return_value = make_response(
            content=json.dumps({"authenticated": True, "userId": "42"}),
            cookies={"csrftoken": "def456"},
        )

        result = self.bot.login()

        self.assertTrue(result["authenticated"])
        self.assertEqual(self.bot.user_id, "42")

    @patch("insta_bot.src.insta_bot.requests.Session")
    def test_failed_login_does_not_set_user_id(self, session_cls):
        session = session_cls.return_value
        session.get.return_value = make_response(
            cookies={"csrftoken": "abc123"}
        )
        session.post.return_value = make_response(
            content=json.dumps({"authenticated": False}),
            cookies={"csrftoken": "def456"},
        )

        result = self.bot.login()

        self.assertFalse(result["authenticated"])
        self.assertFalse(hasattr(self.bot, "user_id"))

    @patch("insta_bot.src.insta_bot.requests.Session")
    def test_connection_error_is_handled_gracefully(self, session_cls):
        session = session_cls.return_value
        session.get.side_effect = requests.exceptions.ConnectionError

        result = self.bot.login()

        self.assertIsNone(result)


class GetUserIdTest(unittest.TestCase):
    def setUp(self):
        self.bot = InstaBot(username="alice", password="s3cret")
        self.bot.session = MagicMock()

    def test_returns_user_id_when_found(self):
        self.bot.session.get.return_value = make_response(
            status_code=200,
            content=json.dumps({"graphql": {"user": {"id": "999"}}}),
        )

        user_id = self.bot.get_userid("bob")

        self.assertEqual(user_id, "999")

    def test_returns_none_when_request_fails(self):
        self.bot.session.get.return_value = make_response(status_code=404)

        user_id = self.bot.get_userid("bob")

        self.assertIsNone(user_id)


class FollowUnfollowUserTest(unittest.TestCase):
    def setUp(self):
        self.bot = InstaBot(username="alice", password="s3cret")
        self.bot.session = MagicMock()

    def test_follow_user_succeeds(self):
        self.bot.session.post.return_value = make_response(
            status_code=200, content="ok"
        )

        self.assertTrue(self.bot.follow_user(userid="123"))

    def test_follow_user_fails_on_bad_status(self):
        self.bot.session.post.return_value = make_response(
            status_code=400, content="ok"
        )

        self.assertFalse(self.bot.follow_user(userid="123"))

    def test_follow_user_fails_when_rate_limited(self):
        self.bot.session.post.return_value = make_response(
            status_code=200, content="Please wait a few minutes"
        )

        self.assertFalse(self.bot.follow_user(userid="123"))

    def test_unfollow_user_succeeds(self):
        self.bot.session.post.return_value = make_response(
            status_code=200, content="ok"
        )

        self.assertTrue(self.bot.unfollow_user(userid="123"))

    def test_unfollow_user_fails_on_bad_status(self):
        self.bot.session.post.return_value = make_response(
            status_code=500, content="ok"
        )

        self.assertFalse(self.bot.unfollow_user(userid="123"))


if __name__ == "__main__":
    unittest.main()
