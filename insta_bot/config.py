"""Static configuration values used throughout the bot.

Keeping these values in a single module makes it easy to tweak timings,
endpoints or GraphQL query hashes without hunting through the codebase.
"""
import os

BASE_URL = 'https://www.instagram.com'

USER_AGENT = (
    'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36'
)

# Query hashes for Instagram's (undocumented) GraphQL endpoints.
FOLLOWERS_QUERY_HASH = 'c76146de99bb02f6415203be841dd25a'
FOLLOWING_QUERY_HASH = 'd04b0a864b4b54837c0d870b0e77e076'
SUGGESTED_USERS_QUERY_HASH = 'ed2e3ff5ae8b96717476b62ef06ed8cc'

# Directory where follower/following snapshots are cached, relative to the
# package itself so the bot behaves the same regardless of the current
# working directory it is launched from.
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')

DEFAULT_PAGE_SIZE = 24
SUGGESTED_USERS_COUNT = 30

# How long to back off when Instagram starts rate limiting requests.
FOLLOW_RETRY_DELAY_SECONDS = 10 * 60
ERROR_RETRY_DELAY_SECONDS = 3 * 60

# Safety cap on how many accounts are unfollowed per cycle.
MAX_UNFOLLOW_BATCH = 50
