"""Hindi narration written locally for post-render mixing."""
import asyncio
import os
from pathlib import Path


def synthesize(text: str, target: Path, checkpoint, voice: str | None = None) -> Path:
    """Write one Hindi narration file without storing API credentials or request logs."""
    if target.exists():
        return target
    if not text.strip():
        raise RuntimeError('Cannot synthesize an empty narration line.')
    import edge_tts
    target.parent.mkdir(parents=True, exist_ok=True)
    checkpoint()
    selected = voice or os.getenv('LOCAL_TTS_VOICE', 'hi-IN-SwaraNeural')
    temporary = target.with_suffix('.partial.mp3')
    async def create():
        await edge_tts.Communicate(text, voice=selected, rate=os.getenv('LOCAL_TTS_RATE', '-4%')).save(str(temporary))
    try:
        asyncio.run(create())
        if not temporary.exists() or not temporary.stat().st_size:
            raise RuntimeError('No audio returned.')
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise RuntimeError('Local Hindi narration generation failed. Check local TTS availability and voice configuration.') from None
    return target
