"""Bounded course-reference context for structured-writing requests."""
from .config import ROOT


def excerpt(limit=4000):
    """Return a stable, compact reference excerpt within provider input limits."""
    source = (ROOT / 'docs/client-prompts.txt').read_text(encoding='utf-8').replace('\x00', '')
    normalized = ' '.join(source.split())
    return normalized[:limit]
