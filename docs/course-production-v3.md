# Automated course production

The creative input is a title. Accounts connect their own encrypted Google API key once. New requests default to live Hindi, 16:9, native character dialogue plus separate AI Studio narration. Optional production settings support other languages and demo output.

## Production sequence

1. Read the backend course source and six-act writing rules. Generate a fresh concept and blueprint. Critique and revise up to three drafts; compare against recent scripts belonging to this account. Lock the accepted words.
2. Extract tagged characters and voice direction. Generate and inspect canonical references, with at most two image attempts.
3. Extract empty locations and two or three camera angles. Generate and inspect the plates. Record their hashes in the asset manifest.
4. Plan six shots and select a saved background angle for each. Save a scene packet with exact language, spoken words, speaker, character tags, angle, still prompt, animation, audio direction and negatives.
5. Compose scene stills from the saved character references and selected background plate. Inspect identity and scene requirements, with one corrective retry.
6. Animate the still. Native dialogue is copied from the locked script; narrator scenes instruct every mouth to stay closed. Inspect sampled identity frames and video performance. Independently transcribe dialogue and compare normalized words exactly. Retry a failed completed generation once. Unknown video submission outcomes are never automatically resubmitted.
7. Generate and transcribe separate narrator speech. Trim outside the estimated speech window; apply the same timing change to native video and audio, preserve all verified words, and pad the remaining scene with a held final frame. Reject speech requiring more than 25% acceleration.
8. Assemble six 7.5-second scenes (45 seconds total). Add speech-window captions, short fades, synthesized original ambience/effects or configured licensed BGM, and duck music under speech. Check streams, dimensions, duration and the mixed-film transcript.
9. Generate publishing metadata from the locked finished story. Create reference-guided thumbnail art with a separately rendered Unicode title. Export the film and production kit.

## Operational boundaries

- Paid Google API billing and quota are required. Consumer Flow credits do not automatically fund Gemini API calls.
- Image attempts are bounded at two, video attempts at two per scene and narration attempts at two. Retries increase cost; a provider outage or exhausted quota pauses the production with saved work.
- Transcription and visual review are model judgments. They can reject valid output or miss defects. Speech timestamps are estimates, not forced alignment. Native Veo voice identity and frame-perfect character or lip-sync consistency are not guaranteed.
- The current music fallback is synthesized ambience; it is not a licensed premium music catalog.
- The workflow exports a publishing package; it does not upload to YouTube.
- The distributed queue isolates accounts and keys. Worker capacity determines concurrent renders; queued users do not each receive a dedicated worker.

## Verification

Automated tests cover account access, queue ownership, uncertain operation preservation, exact transcript comparisons (including Devanagari marks), background angle validation, bounded image retries, a six-scene simulated live-provider pipeline, and real FFmpeg speech-window rendering. Full live Google production still requires enabled billing and sufficient quota; mock-provider tests do not establish generated-film quality.
