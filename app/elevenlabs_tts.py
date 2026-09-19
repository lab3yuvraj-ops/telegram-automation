"""Durable ElevenLabs narration generation for the final mix."""
import hashlib
import os
from pathlib import Path
import httpx
from . import store


def available():
    return bool(os.getenv('ELEVENLABS_API_KEY', '').strip() and os.getenv('ELEVENLABS_VOICE_ID', '').strip())


def synthesize(text: str, target: Path, checkpoint):
    if target.exists():
        return target
    key = os.getenv('ELEVENLABS_API_KEY', '').strip()
    voice = os.getenv('ELEVENLABS_VOICE_ID', '').strip()
    if not key or not voice:
        raise RuntimeError('ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID are required. No narration was generated.')
    model = os.getenv('ELEVENLABS_MODEL', 'eleven_multilingual_v2')
    journal = target.with_suffix('.operation.json')
    record = {
        'provider': 'elevenlabs', 'voice_id': voice, 'model': model,
        'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'status': 'submitting', 'done': False, 'attempt': 1,
    }
    if journal.exists():
        saved = store.read(journal)
        if any(saved.get(key) != record[key] for key in ('voice_id', 'model', 'text_sha256')):
            raise RuntimeError('Saved ElevenLabs inputs differ. Inspect the existing operation before changing it.')
        if saved.get('done') and saved.get('status') != 'failed':
            raise RuntimeError('Saved ElevenLabs audio is missing. Inspect the existing operation before regenerating it.')
        if saved.get('status') == 'failed':
            # A new /resume is explicit authorization to retry a known failed
            # request; retain the old record and keep the retry bounded.
            previous = int(saved.get('attempt', 1))
            if previous >= int(os.getenv('ELEVENLABS_MAX_ATTEMPTS', '2')):
                raise RuntimeError('ElevenLabs narration failed twice. Check the saved operation before another retry.')
            store.save(target.with_name(target.stem+f'-attempt-{previous}.operation.json'), saved)
            record['attempt'] = previous + 1
            store.save(journal, record)
    else:
        store.save(journal, record)
    checkpoint()
    try:
        response = httpx.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128',
            headers={'xi-api-key': key, 'Content-Type': 'application/json'},
            json={'text': text, 'model_id': model, 'voice_settings': {'stability': 0.55, 'similarity_boost': 0.75, 'style': 0.15, 'use_speaker_boost': True}},
            timeout=180,
        )
        response.raise_for_status()
        audio = response.content
        if not audio:
            raise ValueError('Empty audio')
    except (httpx.HTTPError, ValueError) as exc:
        detail = 'request failed'
        if isinstance(exc, httpx.HTTPStatusError):
            detail = f'HTTP {exc.response.status_code}: {exc.response.text[:500]}'
        detail = detail.replace(key, '[redacted]')
        record.update(status='failed', done=True, error=detail); store.save(journal, record)
        raise RuntimeError('ElevenLabs narration generation failed; check the saved operation for the provider response.') from None
    temporary = target.with_suffix('.partial.mp3')
    temporary.write_bytes(audio); temporary.replace(target)
    record.update(status='succeeded', done=True, audio_sha256=hashlib.sha256(audio).hexdigest())
    store.save(journal, record)
    return target
