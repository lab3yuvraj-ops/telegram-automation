from app import auth


def test_encryption_key_is_optional_for_telegram_only_setup(monkeypatch):
    monkeypatch.delenv('APP_ENCRYPTION_KEY', raising=False)
    monkeypatch.setattr(auth, '_ephemeral_key', None)
    first = auth.cipher()
    token = first.encrypt(b'test')
    assert auth.cipher().decrypt(token) == b'test'
