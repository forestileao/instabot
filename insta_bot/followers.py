"""Fetching (paginated) follower/following relationships from Instagram.

The three original bot methods (``map_followers``, ``map_following`` and
``map_user_followers``) were near-identical copies of the same pagination
loop. They are consolidated here into a single, well tested implementation.
"""
import json
import logging

from . import config

logger = logging.getLogger(__name__)


class FollowerMapper:
    def __init__(self, client):
        self.client = client

    def followers(self, user_id, limit=None, verbose=False):
        """Return the accounts following ``user_id``."""
        return self._fetch_connections(
            user_id, config.FOLLOWERS_QUERY_HASH, 'edge_followed_by', limit=limit, verbose=verbose
        )

    def following(self, user_id, limit=None, verbose=False):
        """Return the accounts ``user_id`` is following."""
        return self._fetch_connections(
            user_id, config.FOLLOWING_QUERY_HASH, 'edge_follow', limit=limit, verbose=verbose
        )

    def suggested(self):
        """Return Instagram's list of suggested accounts to follow."""
        variables = {
            'fetch_media_count': 0,
            'fetch_suggested_count': config.SUGGESTED_USERS_COUNT,
            'ignore_cache': True,
            'filter_followed_friends': True,
            'seen_ids': [],
            'include_reel': True,
        }
        payload = self.client.get_json(
            '/graphql/query/',
            params={'query_hash': config.SUGGESTED_USERS_QUERY_HASH, 'variables': json.dumps(variables)},
        )

        edges = payload.get('data', {}).get('user', {}).get('edge_suggested_users', {}).get('edges', [])
        suggestions = []
        for edge in edges:
            node = edge['node']
            # Skip Instagram's own "Ins..." promotional suggestions.
            if node.get('description', '').startswith('Ins'):
                continue
            suggestions.append({'username': node['user']['username'], 'id': node['user']['id']})
        return suggestions

    def _fetch_connections(self, user_id, query_hash, edge_key, limit=None, verbose=False):
        connections = []
        cursor = None

        while True:
            variables = {
                'id': user_id,
                'include_reel': True,
                'fetch_mutual': cursor is None,
                'first': config.DEFAULT_PAGE_SIZE,
            }
            if cursor is not None:
                variables['after'] = cursor

            payload = self.client.get_json(
                '/graphql/query/',
                params={'query_hash': query_hash, 'variables': json.dumps(variables)},
            )

            if payload.get('status') == 'fail':
                break

            edge = payload['data']['user'][edge_key]
            for item in edge['edges']:
                node = item['node']
                connections.append({'username': node['username'], 'id': node['id']})
                if verbose:
                    logger.info('added %s', node['username'])

                if limit is not None and len(connections) >= limit:
                    return connections

            page_info = edge['page_info']
            if not page_info.get('has_next_page'):
                break
            cursor = page_info['end_cursor']

        return connections
