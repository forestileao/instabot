"""High level bot orchestration: follows and unfollows accounts.

This module wires together :class:`~insta_bot.client.InstagramClient` (HTTP
plumbing) and :class:`~insta_bot.followers.FollowerMapper` (pagination) into
the two behaviours the bot exposes:

* follow either a target account's followers, or Instagram's suggested
  users, until ``hoped_followers`` new accounts have been followed.
* unfollow accounts that don't follow back.
"""
import logging
import threading
import time

from . import cache, config
from .client import InstagramClient
from .followers import FollowerMapper

logger = logging.getLogger(__name__)


class InstaBot:
    def __init__(self, username, password):
        self.client = InstagramClient(username, password)
        self.mapper = FollowerMapper(self.client)

        self.target_username = ''
        self.hoped_followers = 0
        self.unfollow_all_not_followers = True
        self.verbose = False

    def start(self, target_username='', hoped_followers=2000, unfollow_all_not_followers=True, verbose=False):
        """Log in and start the follow/unfollow loops as background threads."""
        self.target_username = target_username
        self.hoped_followers = hoped_followers
        self.unfollow_all_not_followers = unfollow_all_not_followers
        self.verbose = verbose

        self.client.login()
        logger.info('Logged in (user=%s, id=%s)', self.client.username, self.client.user_id)

        follow_thread = threading.Thread(target=self._follow_loop, daemon=True)
        unfollow_thread = threading.Thread(target=self._unfollow_loop, daemon=True)
        follow_thread.start()
        unfollow_thread.start()
        return follow_thread, unfollow_thread

    # -- Following --------------------------------------------------------

    def _get_follow_candidates(self):
        if self.target_username:
            target_id = self.client.get_user_id(self.target_username)
            followers = self.mapper.followers(target_id, verbose=self.verbose)
            cache.save('target-followers.json', followers)
            return followers
        return self.mapper.suggested()

    def _follow_batch(self, followed_count):
        """Try to follow one batch of candidates, returning the updated count."""
        candidates = self._get_follow_candidates()
        if not candidates:
            logger.warning('No follow candidates found, retrying later')
            time.sleep(config.ERROR_RETRY_DELAY_SECONDS)
            return followed_count

        for user in candidates:
            if followed_count >= self.hoped_followers:
                break

            if self.client.follow(user['id']):
                followed_count += 1
                logger.info('Followed %s (%s/%s)', user['username'], followed_count, self.hoped_followers)
            else:
                logger.info('Rate limited, waiting before next follow request')
                time.sleep(config.FOLLOW_RETRY_DELAY_SECONDS)

        return followed_count

    def _follow_loop(self):
        followed_count = 0
        while followed_count < self.hoped_followers:
            try:
                followed_count = self._follow_batch(followed_count)
            except Exception:
                logger.exception('Error while following users')
                time.sleep(config.ERROR_RETRY_DELAY_SECONDS)

    # -- Unfollowing --------------------------------------------------------

    def _unfollow_once(self):
        """Run a single unfollow cycle, returning (followers, following) counts."""
        followers = self.mapper.followers(self.client.user_id, verbose=self.verbose)
        following = self.mapper.following(self.client.user_id, verbose=self.verbose)
        cache.save('followers.json', followers)
        cache.save('following.json', following)

        follower_ids = {user['id'] for user in followers}
        non_followers = [user for user in following if user['id'] not in follower_ids]

        logger.info('Followers: %s, Following: %s', len(followers), len(following))

        for user in non_followers[:config.MAX_UNFOLLOW_BATCH]:
            while not self.client.unfollow(user['id']):
                logger.info('Rate limited, waiting before next unfollow request')
                time.sleep(config.FOLLOW_RETRY_DELAY_SECONDS)
            logger.info('Unfollowed %s', user['username'])

        return len(followers), len(following)

    def _unfollow_loop(self):
        while True:
            try:
                followers_count, following_count = self._unfollow_once()
            except Exception:
                logger.exception('Error while unfollowing users')
                time.sleep(config.ERROR_RETRY_DELAY_SECONDS)
                continue

            if not self.unfollow_all_not_followers and following_count <= followers_count:
                break
