"""Cloudflare Workers AI image generation adapter.

FLUX.2 Klein supports text generation and editing. The adapter accepts optional
local reference images and sends them as data URIs, preserving the distinction
between a text-only draft and a reference-composed scene.
"""
import base64, hashlib, os
from pathlib import Path
import httpx
from PIL import Image
from .config import STYLE
from .store import save

MODEL = '@cf/black-forest-labs/flux-2-klein-4b'

def enabled():
    return os.getenv('IMAGE_PROVIDER', 'replicate_pruna') == 'cloudflare_flux'

def _data_uri(path: Path) -> str:
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode('ascii')

def generate(prompt, path, checkpoint, aspect='16:9', refs=()):
    token = os.getenv('CLOUDFLARE_API_TOKEN', '').strip()
    account = os.getenv('CLOUDFLARE_ACCOUNT_ID', '').strip()
    if not token or not account:
        raise RuntimeError('Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID to enable Cloudflare images.')
    width, height = (1024, 576) if aspect == '16:9' else (576, 1024)
    seed = int(hashlib.sha256((str(path) + prompt).encode()).hexdigest()[:8], 16) % 2147483647
    body = {'prompt': STYLE + '\n' + prompt, 'width': width, 'height': height, 'steps': 4, 'seed': seed}
    for i, (_, ref) in enumerate(refs[:4], 1):
        body[f'input_image_{i}' if i > 1 else 'input_image'] = _data_uri(ref)
    checkpoint()
    endpoint = f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{MODEL}'
    try:
        # Klein's Workers AI endpoint is multipart; scalar fields and optional
        # data-URI references are sent as form parts.
        response = httpx.post(endpoint, headers={'Authorization': 'Bearer ' + token},
                              files={key: (None, str(value)) for key, value in body.items()}, timeout=300)
    except httpx.HTTPError:
        raise RuntimeError('Cloudflare image generation connection interrupted. Resume to retry.') from None
    if response.status_code != 200:
        if response.status_code in (401, 403):
            raise RuntimeError('Cloudflare rejected the API token or account permissions.')
        if response.status_code in (402, 429):
            raise RuntimeError('Cloudflare image generation quota or capacity limit reached. Resume after it resets.')
        raise RuntimeError(f'Cloudflare image generation failed (HTTP {response.status_code}).')
    try:
        payload = response.json()
        encoded = payload['result']['image']
        raw = base64.b64decode(encoded)
        from io import BytesIO
        image = Image.open(BytesIO(raw)).convert('RGB')
    except Exception:
        raise RuntimeError('Cloudflare returned an invalid image response.') from None
    if image.size != (width, height):
        raise RuntimeError('Cloudflare returned an unexpected image size; refusing an unverified output.')
    temp = path.with_suffix('.tmp')
    image.save(temp, format='PNG')
    temp.replace(path)
    save(path.with_suffix('.generation.json'), {
        'provider': 'cloudflare-workers-ai', 'model': MODEL,
        'width': width, 'height': height, 'seed': seed,
        'estimated_usd': 0.0001, 'reference_images': len(refs),
    })
