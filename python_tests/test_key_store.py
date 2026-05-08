from wechat_overlay.key_store import load_key, save_key


def test_save_and_load_key_round_trips(tmp_path) -> None:
    path = tmp_path / "key.txt"

    save_key("secret", path)

    assert load_key(path) == "secret"


def test_load_key_returns_empty_for_missing_file(tmp_path) -> None:
    assert load_key(tmp_path / "missing.txt") == ""
