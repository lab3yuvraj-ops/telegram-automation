import httpx

from app import telegram_bot as tg, zernio
from tests.test_telegram import complete, service, update


def test_review_requires_explicit_approval_and_never_publishes_when_disabled(service, monkeypatch):
    job = complete(service)
    service.notify()
    assert any('/approve' in call[1].get('text', '') for call in service.api.calls)
    monkeypatch.setenv('YOUTUBE_PUBLISH_ENABLED', 'false')
    called = []
    monkeypatch.setattr(zernio, 'publish_youtube', lambda *args: called.append(args))
    service.handle(update('/approve', ident=2))
    assert called == []
    assert tg.review(job['id'])['state'] == 'approved'
    assert 'nothing has been posted' in service.api.calls[-1][1]['text']


def test_rejection_requires_a_second_command_before_paid_regeneration(service, monkeypatch):
    job = complete(service)
    service.notify()
    service.handle(update('/reject', ident=2))
    assert tg.review(job['id'])['state'] == 'rejected'
    assert '/regenerate' in service.api.calls[-1][1]['text']
    regenerated = []
    monkeypatch.setattr(tg.pipeline, 'regenerate', lambda ident, number: regenerated.append((ident, number)))
    service.handle(update('/regenerate', ident=3))
    assert regenerated == []
    service.handle(update('/scene 2', ident=4))
    assert regenerated == [(job['id'], 2)]


def test_zernio_verify_is_read_only(monkeypatch):
    monkeypatch.setenv('ZERNIO_API_KEY', 'test-key')
    calls = []
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs['headers']))
        return httpx.Response(200, json={'profiles': [{}]}, request=httpx.Request(method, url))
    monkeypatch.setattr(httpx, 'request', request)
    assert zernio.verify() == {'authenticated': True, 'profile_count': 1}
    assert calls[0][0] == 'GET' and calls[0][1].endswith('/profiles')


def test_zernio_publish_requires_explicit_opt_in(tmp_path, monkeypatch):
    monkeypatch.setenv('ZERNIO_API_KEY', 'test-key')
    monkeypatch.setenv('YOUTUBE_PUBLISH_ENABLED', 'false')
    video = tmp_path / 'film.mp4'; video.write_bytes(b'mp4')
    try:
        zernio.publish_youtube(video, {'titles': ['Title']}, 'job')
    except zernio.ZernioError as exc:
        assert 'disabled' in str(exc)
    else:
        raise AssertionError('publishing without explicit opt-in must fail')
