"""Small helper around persisting JSON snapshots to the package cache dir."""
import json
import os

from . import config


def _resolve_path(filename):
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    return os.path.join(config.CACHE_DIR, filename)


def save(filename, data):
    """Persist ``data`` as JSON under the package cache directory."""
    with open(_resolve_path(filename), 'w') as outfile:
        json.dump(data, outfile)


def load(filename):
    """Load JSON previously stored with :func:`save`.

    Returns ``None`` if no cache file exists yet.
    """
    path = _resolve_path(filename)
    if not os.path.exists(path):
        return None
    with open(path) as infile:
        return json.load(infile)
