from insta_bot import cache, config


def test_save_then_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'CACHE_DIR', str(tmp_path))

    cache.save('followers.json', [{'username': 'alice', 'id': '1'}])

    assert cache.load('followers.json') == [{'username': 'alice', 'id': '1'}]


def test_load_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'CACHE_DIR', str(tmp_path))

    assert cache.load('does-not-exist.json') is None


def test_save_creates_cache_dir_if_missing(tmp_path, monkeypatch):
    target_dir = tmp_path / 'nested' / 'cache'
    monkeypatch.setattr(config, 'CACHE_DIR', str(target_dir))

    cache.save('following.json', [])

    assert target_dir.exists()
