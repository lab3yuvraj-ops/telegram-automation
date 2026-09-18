"""Budget text-to-image route. Never discard reference images silently."""
import os,hashlib
from .config import STYLE

MODEL='black-forest-labs/FLUX.1-schnell'
PROVIDER='fal-ai'

def enabled():return os.getenv('IMAGE_PROVIDER','replicate_pruna')=='hf_schnell_hybrid'

def generate(prompt,path,checkpoint,aspect='16:9',refs=()):
    if refs:raise ValueError('FLUX Schnell text-to-image cannot compose saved references')
    token=os.getenv('HF_TOKEN','').strip()
    if not token:raise RuntimeError('Set HF_TOKEN in .env and Railway to enable Hugging Face images.')
    from huggingface_hub import InferenceClient
    checkpoint()
    width,height=(1024,576) if aspect=='16:9' else (576,1024)
    # Stable within one asset, distinct between scenes and corrective attempts.
    seed=int(hashlib.sha256((str(path)+prompt).encode()).hexdigest()[:8],16)%2147483647
    try:
        client=InferenceClient(provider=PROVIDER,api_key=token,timeout=180)
        image=client.text_to_image(STYLE+'\n'+prompt,model=MODEL,width=width,height=height,num_inference_steps=4,seed=seed)
    except Exception as exc:
        status=getattr(getattr(exc,'response',None),'status_code',None)
        reason='Check HF token permissions and remaining Inference Providers credits.' if status in (401,402,403,429) else 'Provider unavailable; resume to reuse saved assets.'
        raise RuntimeError('Hugging Face image generation paused. '+reason) from None
    if image.size!=(width,height):raise RuntimeError('Hugging Face returned an unexpected image size; refusing an unverified output.')
    temp=path.with_suffix('.tmp')
    image.convert('RGB').save(temp,format='PNG');temp.replace(path)
    from .store import save
    save(path.with_suffix('.generation.json'),{'provider':'huggingface:'+PROVIDER,'model':MODEL,'width':width,'height':height,'seed':seed,'estimated_usd':.003,'reference_images':0})
