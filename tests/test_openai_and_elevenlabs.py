import httpx
from pydantic import BaseModel
from app import openai_text, elevenlabs_tts


class Result(BaseModel):
    title: str


def test_openai_uses_structured_schema(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-4.1-mini')
    def post(url, **kwargs):
        assert url == 'https://api.openai.com/v1/chat/completions'
        assert kwargs['json']['model'] == 'gpt-4.1-mini'
        assert kwargs['json']['response_format']['json_schema']['schema'] == Result.model_json_schema()
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"title":"A new story"}'}}]})
    monkeypatch.setattr(httpx, 'post', post)
    assert openai_text.structured('test', Result, lambda: None) == {'title': 'A new story'}


def test_elevenlabs_persists_audio_and_journal(tmp_path, monkeypatch):
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-key')
    monkeypatch.setenv('ELEVENLABS_VOICE_ID', 'voice-id')
    def post(url, **kwargs):
        assert 'voice-id' in url
        assert kwargs['json']['model_id'] == 'eleven_multilingual_v2'
        return httpx.Response(200, content=b'ID3audio', request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    target = tmp_path / 'speech-01.mp3'
    elevenlabs_tts.synthesize('नमस्ते', target, lambda: None)
    assert target.read_bytes() == b'ID3audio'
    assert target.with_suffix('.operation.json').exists()
