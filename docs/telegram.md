# Nightfall on Telegram

Telegram replaces the dashboard. HTTP exposes only `/healthz`; login, signup, files, studio UI and browser job endpoints are removed. Existing film assets and account data are retained. The previous UI source is archived locally under `data/retired-dashboard` and excluded from deployment.

## Connect when ready

1. Create a bot through Telegram's official `@BotFather` and copy its bot token into `TELEGRAM_BOT_TOKEN` in `.env.telegram`.
2. Start the backend with `python run.py`. Send `/start` to the bot. It replies with your private chat ID even before production access is enabled.
3. Set `TELEGRAM_ALLOWED_USER_IDS` to a comma-separated list of approved Telegram user IDs. Only those private chats can submit titles; groups are ignored.
4. Keep `REPLICATE_API_TOKEN`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, and `ELEVENLABS_VOICE_ID` in `.env`. `APP_ENCRYPTION_KEY` is optional for this Telegram-only deployment; when omitted, encrypted legacy credentials are only usable until the process restarts. Enable Replicate billing and `ALLOW_PAID_GENERATION=true` for live films. `TELEGRAM_PRODUCTION_MODE=demo` exercises delivery without external calls.
5. Send only the title. The bot queues production, updates its progress message, and uploads the finished MP4 to the same private chat.

No personal Telegram login, phone number, API ID/hash or webhook is required. This implementation uses Bot API long polling. If this bot already has a webhook, remove it before starting polling; the backend will not silently take over another integration.

## Commands

`/start`, `/help`, `/id`, `/status`, `/cancel`, `/resume`, `/scene 3`, `/video`, `/script`, `/approve`, `/reject`, `/regenerate`, and `/keep`. `/scene N` regenerates that scene of the latest stopped film, using paid APIs in live mode.

Status, cancellation and resumption target the latest production in the same chat. `/video` sends the latest completed film again. `/script` sends a JSON document with the latest script and publishing metadata. Bot chats are not end-to-end encrypted; keep provider keys in Railway secrets rather than messages.

After the final MP4 is delivered, the bot asks for `/approve` or `/reject`. Rejection is non-billable and asks whether to regenerate; `/regenerate` then requires a specific `/scene N` choice. Approval only posts when all three Zernio settings are intentionally configured: `ZERNIO_API_KEY`, `ZERNIO_YOUTUBE_ACCOUNT_ID`, and `YOUTUBE_PUBLISH_ENABLED=true`. Otherwise it records approval and makes no external post. The Zernio publishing adapter uses the generated title, description and tags, marks the YouTube upload as synthetic media, and has a per-job idempotency key to avoid duplicate creation on a network retry.

## Railway

Reuse the existing PostgreSQL database, private object storage and production workers. The former web service runs `python run.py` with one replica and the Telegram variables. Workers keep `python -m app.worker` and do not need the bot token. Keep `/healthz` as the health check. Without a token the service starts safely but does not connect to Telegram.

## Reliability and limits

- Update offsets and chat-to-job routing persist in the database. A deterministic job ID prevents repeated Telegram updates from creating duplicate paid productions.
- PostgreSQL permits one poller per bot through an advisory lock. Run only one process when using local SQLite.
- Workers continue independently if Telegram is unavailable. Stored final films can be delivered after reconnecting.
- Delivery uploads an MP4 directly, with a compression fallback above 48 MB. It does not expose a public object-storage link.
- Unknown upload outcomes are not automatically resent, because Telegram may already have accepted the video. The bot asks the user to use `/video` if needed. Explicit provider failures are retried after a backoff.
- Replicate prediction failures stop with a Telegram status message. `/resume` reuses saved operations and does not automatically resubmit uncertain predictions.
- Telegram cannot be verified against a real chat until the bot token and allowed chat ID are configured.

Bot API reference: https://core.telegram.org/bots/api
