"""Low level HTTP client for Instagram's private/legacy endpoints.

This module only knows how to talk to Instagram (authenticate, fetch JSON,
follow/unfollow a user id). It has no opinion about *what* should be
followed/unfollowed or *when* -- that logic lives in :mod:`insta_bot.bot`
and :mod:`insta_bot.followers`.
"""
import time

import requests

from . import config


class InstagramClientError(Exception):
    """Raised when the client can't complete a request against Instagram."""


class InstagramClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.user_id = None

        self.session = requests.Session()
        self.session.headers.update({
            'user-agent': config.USER_AGENT,
            'Referer': config.BASE_URL,
        })

    @staticmethod
    def _generate_encrypted_password(password):
        """Build the ``enc_password`` value expected by the login endpoint."""
        timestamp = str(int(time.time()))
        return f'#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{password}'

    def login(self):
        """Authenticate the session and store ``self.user_id``.

        Raises :class:`InstagramClientError` if authentication fails or the
        connection can't be established.
        """
        try:
            response = self.session.get(config.BASE_URL)
            self.session.headers.update({'x-csrftoken': response.cookies['csrftoken']})

            login_data = {
                'username': self.username,
                'enc_password': self._generate_encrypted_password(self.password),
            }
            response = self.session.post(
                f'{config.BASE_URL}/accounts/login/ajax/',
                data=login_data,
                allow_redirects=True,
            )
            self.session.headers.update({'x-csrftoken': response.cookies['csrftoken']})
            payload = response.json()
        except requests.exceptions.ConnectionError as exc:
            raise InstagramClientError('Connection refused while logging in') from exc
        except ValueError as exc:
            raise InstagramClientError('Unexpected (non-JSON) login response') from exc

        if not payload.get('authenticated'):
            raise InstagramClientError(f'Login failed: {payload}')

        self.user_id = payload['userId']
        return payload

    def get_user_id(self, username):
        """Resolve a username to its numeric Instagram user id."""
        response = self.session.get(f'{config.BASE_URL}/{username}/', params={'__a': 1})
        if response.status_code != 200:
            return None

        try:
            return response.json()['graphql']['user']['id']
        except (ValueError, KeyError) as exc:
            raise InstagramClientError(
                f'Unexpected response while resolving user id for {username!r}'
            ) from exc

    def get_json(self, path, params=None):
        """GET ``path`` and return the decoded JSON body."""
        response = self.session.get(f'{config.BASE_URL}{path}', params=params)
        try:
            return response.json()
        except ValueError as exc:
            raise InstagramClientError(f'Invalid JSON response from {path}') from exc

    def follow(self, user_id):
        return self._post_relationship(user_id, 'follow')

    def unfollow(self, user_id):
        return self._post_relationship(user_id, 'unfollow')

    def _post_relationship(self, user_id, action):
        response = self.session.post(f'{config.BASE_URL}/web/friendships/{user_id}/{action}/')
        if response.status_code != 200:
            return False
        # Instagram replies with a "Please wait a few minutes..." style body
        # (starting with "Ple...") when the account is being rate limited,
        # even though the HTTP status code itself is a 200.
        return not response.text.startswith('Ple')
