# Nightfall Telegram video backend

Send a title in a private Telegram chat. The backend writes and checks a six-act horror story, creates canonical character and background references with Nano Banana, composes six scenes, generates Pruna video clips, layers Hindi narration, and sends a 45-second 16:9 film back to that chat.

Telegram is the entire user interface. The dashboard, signup, login, browser API and static frontend are no longer served. Existing production data is preserved.

## Setup

1. Install Python dependencies with `pip install -r requirements.txt`; install FFmpeg and FFprobe.
2. Fill `TELEGRAM_BOT_TOKEN` in `.env.telegram`, and set `TELEGRAM_ALLOWED_USER_IDS` to the approved private-chat IDs. A blank token leaves Telegram disabled. Groups are ignored.
3. Keep your existing `.env`, encryption key and Replicate token. For a fresh setup, start from `.env.example` and generate a Fernet key. Set `OPENAI_API_KEY` for writing and `ELEVENLABS_API_KEY` plus `ELEVENLABS_VOICE_ID` for Hindi narration.
4. Run `python run.py`. Use one local process. Send your title to the bot.

Live generation requires a Replicate token with Nano Banana and Pruna P-Video-2 access, an OpenAI API key for structured writing, and an ElevenLabs API key plus voice ID for Hindi narration. Telegram defaults to `TELEGRAM_AUDIO_MODE=elevenlabs`, which layers narration after video generation. Set `TELEGRAM_PRODUCTION_MODE=demo` for a no-generation-cost assembly/delivery test.

## Railway

The Telegram service runs `python run.py` with one replica and health endpoint `/healthz`. Existing worker services run `python -m app.worker`; PostgreSQL and private S3 storage are shared. Add the same media, OpenAI and ElevenLabs variables to every service that can run a worker. Set Telegram variables only on the Telegram service. Worker model, encryption and storage variables remain unchanged.

## Optional YouTube publishing through Zernio

Finished videos always require a Telegram `/approve` decision. Configure `ZERNIO_API_KEY` and `ZERNIO_YOUTUBE_ACCOUNT_ID` after connecting the intended YouTube account in Zernio. Keep `YOUTUBE_PUBLISH_ENABLED=false` until the deployment owner is ready for real posts. When enabled, approval uploads the completed MP4 and creates one YouTube post using the first generated title, the generated description and tags. `YOUTUBE_VISIBILITY` defaults to `public`; choose `unlisted` or `private` before enabling if that is the intended release mode.

## Controls

`/status`, `/cancel`, `/resume`, `/video`, `/script`, `/scene`, `/approve`, `/reject`, `/regenerate`, `/keep`, `/help` and `/id` work inside Telegram. Only user IDs in `TELEGRAM_ALLOWED_USER_IDS` can create paid productions.

## Verification

Run `python -m pytest -q`. Tests include Telegram routing, account boundaries, duplicate update handling, uncertain uploads, direct MP4 delivery, production quality gates, real speech trimming and a real 60-second demo render. Mock Telegram tests do not verify live Telegram delivery; that requires credentials.

See [Telegram operations](docs/telegram.md) and [production workflow](docs/course-production-v3.md). AI identity checks and retries improve consistency but cannot guarantee perfect character appearance, voice identity or lip sync.
