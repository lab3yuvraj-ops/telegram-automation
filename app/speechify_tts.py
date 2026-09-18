"""Durable Speechify Hindi speech synthesis for rendered scene audio."""
import base64
import hashlib
import json
import os
from pathlib import Path
import httpx
from . import store


def available():
    return bool(os.getenv('SPEECHIFY_API_KEY', '').strip())


def synthesize(text, target, checkpoint, voice=None):
    """Create a single saved Hindi line; never resubmit an already saved audio file."""
    if target.exists():
        return target
    key = os.getenv('SPEECHIFY_API_KEY', '').strip()
    if not key:
        raise RuntimeError('SPEECHIFY_API_KEY is missing. No Speechify audio was generated.')
    voice = voice or os.getenv('SPEECHIFY_VOICE_ID', 'aadi')
    journal = target.with_suffix('.operation.json')
    record = {
        'provider': 'speechify', 'voice_id': voice, 'language': 'hi-IN',
        'model': 'simba-3.0', 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'status': 'submitting', 'done': False,
    }
    if journal.exists():
        saved = store.read(journal)
        if saved.get('text_sha256') != record['text_sha256'] or saved.get('voice_id') != voice:
            raise RuntimeError('Saved Speechify inputs differ. Inspect the existing operation before changing it.')
        if saved.get('done'):
            raise RuntimeError('Saved Speechify audio is missing. Inspect the existing operation before regenerating it.')
    else:
        store.save(journal, record)
    checkpoint()
    try:
        response = httpx.post('https://api.speechify.ai/v1/audio/speech', headers={
            'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'
        }, json={
            'input': text, 'voice_id': voice, 'language': 'hi-IN',
            'audio_format': 'wav', 'model': 'simba-3.0'
        }, timeout=180)
        response.raise_for_status()
        payload = response.json()
        data = base64.b64decode(payload['audio_data'])
    except (httpx.HTTPError, ValueError, KeyError):
        record.update(status='failed', done=True)
        store.save(journal, record)
        raise RuntimeError('Speechify Hindi speech generation failed; check the API key, voice access and quota.') from None
    tmp = target.with_suffix('.tmp')
    tmp.write_bytes(data)
    tmp.replace(target)
    record.update(status='succeeded', done=True, audio_sha256=hashlib.sha256(data).hexdigest())
    store.save(journal, record)
    return target
