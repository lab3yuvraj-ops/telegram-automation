# Nightfall Studio Agent Instructions

## Scope

This project is a Telegram-first horror video automation service. The user sends a title, and the backend produces the complete production package and final video.

Use the Replicate API with Pruna models for all image and video generation. Do not introduce alternate image or video providers unless the project owner explicitly changes this instruction.

## Current media stack

- Images: `prunaai/p-image` for text-to-image generation.
- Reference-based image edits: `prunaai/p-image-edit` when canonical character or location images are supplied.
- Video: `prunaai/p-video-2` for image-to-video generation.
- Replicate authentication: `REPLICATE_API_TOKEN`.
- Image provider selector: `IMAGE_PROVIDER=replicate_pruna`.
- Video provider selector: `VIDEO_PROVIDER=replicate_pruna`.

Keep Replicate credentials in environment variables or Railway secrets. Never print, commit, persist in logs, or include credentials in user-facing output.

## Production workflow

1. Accept a title through Telegram.
2. Generate and validate the structured horror story and six locked spoken beats, one per course act.
3. Extract canonical character tags, appearance descriptions, voice directions and reference prompts.
4. Extract empty location backgrounds and camera angles.
5. Break the story into exactly six scenes in script order.
6. Generate all still images at `1024x576` with a `16:9` aspect ratio.
7. Use reference images for scene composition whenever the scene includes canonical assets.
8. Send each completed still image to Pruna P-Video-2 with its animation and audio instructions.
9. Keep the speaking character as the only moving mouth for dialogue scenes; narrator scenes have no character speech.
10. Generate narration and dialogue audio, assemble scenes in order, mix ambience and music, add captions, and export the final 16:9 video.
11. Send progress updates and the final video or production package back through Telegram.

## Visual requirements

- Use a cinematic 2D Indian horror illustration style.
- Characters must be clearly adult, human and proportionate.
- Avoid oversized heads, exaggerated bodies, chibi styling, distorted hands, extra characters, text and watermarks.
- Preserve each canonical character's face, hairstyle, clothing colors, distinguishing marks and overall proportions across scenes.
- Keep all generated images and video clips in `16:9`.

## Reliability and billing

- Treat every Replicate prediction as billable.
- Persist prediction inputs, outputs and status before moving to the next stage.
- Never resubmit an uncertain prediction automatically. Resume or inspect its saved status first.
- Keep retries bounded and preserve failed candidates for review.
- Do not claim that identity consistency is perfect; report quality-check results accurately.
- Do not start live generation when `REPLICATE_API_TOKEN` is missing.

## Code changes

- Preserve the Telegram interface, durable job state, cancellation, resume behavior and per-user isolation.
- Keep provider-specific code in `app/replicate_provider.py` and route it through the existing provider abstraction.
- Update `.env.example`, tests and deployment configuration when adding a required Replicate setting.
- Run the relevant tests and `python -m compileall -q app data` after changes.
