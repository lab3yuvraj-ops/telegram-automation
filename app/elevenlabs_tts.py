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
        'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'status': 'submitting', 'done': False,
    }
    if journal.exists():
        saved = store.read(journal)
        if any(saved.get(key) != record[key] for key in ('voice_id', 'model', 'text_sha256')):
            raise RuntimeError('Saved ElevenLabs inputs differ. Inspect the existing operation before changing it.')
        if saved.get('done'):
            raise RuntimeError('Saved ElevenLabs audio is missing. Inspect the existing operation before regenerating it.')
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
    except (httpx.HTTPError, ValueError):
        record.update(status='failed', done=True); store.save(journal, record)
        raise RuntimeError('ElevenLabs narration generation failed; check the API key, voice access and quota.') from None
    temporary = target.with_suffix('.partial.mp3')
    temporary.write_bytes(audio); temporary.replace(target)
    record.update(status='succeeded', done=True, audio_sha256=hashlib.sha256(audio).hexdigest())
    store.save(journal, record)
    return target
