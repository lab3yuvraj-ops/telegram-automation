"""Small, explicit Zernio client used only after Telegram approval.

The caller must opt in with YOUTUBE_PUBLISH_ENABLED=true.  This module never
publishes merely because an API key is present.
"""
import os
import uuid
from pathlib import Path

import httpx
from . import config  # Load the same local/Railway environment configuration as the app.

BASE_URL = 'https://zernio.com/api/v1'


class ZernioError(RuntimeError):
    pass


def configured():
    return bool(os.getenv('ZERNIO_API_KEY', '').strip())


def publishing_enabled():
    return os.getenv('YOUTUBE_PUBLISH_ENABLED', 'false').lower() == 'true'


def _headers():
    key = os.getenv('ZERNIO_API_KEY', '').strip()
    if not key:
        raise ZernioError('Zernio is not configured.')
    return {'Authorization': 'Bearer ' + key}


def _request(method, path, *, json=None, headers=None, content=None):
    merged = {**_headers(), **(headers or {})}
    try:
        response = httpx.request(method, BASE_URL + path, json=json, headers=merged, content=content, timeout=120)
    except httpx.HTTPError as exc:
        raise ZernioError('Zernio request failed.') from exc
    if response.is_error:
        raise ZernioError(f'Zernio request failed (HTTP {response.status_code}).')
    try:
        return response.json()
    except ValueError as exc:
        raise ZernioError('Zernio returned an invalid response.') from exc


def verify():
    """Read-only credential test. It never creates a draft, upload, or post."""
    data = _request('GET', '/profiles')
    profiles = data.get('profiles', data if isinstance(data, list) else [])
    return {'authenticated': True, 'profile_count': len(profiles)}


def _presign(video):
    data = _request('POST', '/media/presign', json={
        'filename': video.name,
        'contentType': 'video/mp4',
        'size': video.stat().st_size,
    })
    try:
        return data['uploadUrl'], data['publicUrl']
    except KeyError as exc:
        raise ZernioError('Zernio did not return an upload URL.') from exc


def publish_youtube(video_path, publishing, job_id):
    """Upload one finished MP4 and publish it to the configured YouTube account."""
    if not publishing_enabled():
        raise ZernioError('YouTube publishing is disabled.')
    account = os.getenv('ZERNIO_YOUTUBE_ACCOUNT_ID', '').strip()
    if not account:
        raise ZernioError('ZERNIO_YOUTUBE_ACCOUNT_ID is required to publish.')
    video = Path(video_path)
    if not video.is_file():
        raise ZernioError('Final video is unavailable for YouTube publishing.')
    upload_url, public_url = _presign(video)
    try:
        with video.open('rb') as stream:
            response = httpx.put(upload_url, content=stream, headers={'Content-Type': 'video/mp4'}, timeout=600)
    except httpx.HTTPError as exc:
        raise ZernioError('Video upload to Zernio failed.') from exc
    if response.is_error:
        raise ZernioError(f'Video upload to Zernio failed (HTTP {response.status_code}).')
    title = (publishing.get('titles') or ['Untitled Video'])[0][:100]
    tags = [tag.strip() for tag in publishing.get('tags', '').split(',') if tag.strip()]
    payload = {
        'title': title,
        'content': publishing.get('description', ''),
        'hashtags': publishing.get('hashtags', []),
        'tags': tags,
        'mediaItems': [{'url': public_url, 'type': 'video'}],
        'platforms': [{
            'platform': 'youtube',
            'accountId': account,
            'platformSpecificData': {
                'title': title,
                'visibility': os.getenv('YOUTUBE_VISIBILITY', 'public'),
                'madeForKids': False,
                'containsSyntheticMedia': True,
                'categoryId': '1',
            },
        }],
        'publishNow': True,
        'metadata': {'nightfall_job_id': job_id},
    }
    return _request('POST', '/posts', json=payload, headers={'x-request-id': str(uuid.uuid5(uuid.NAMESPACE_URL, 'nightfall:' + job_id))})
