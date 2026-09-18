# Provider configuration

`TEXT_PROVIDER=groq` routes concept, blueprint, story drafts, critiques, cast extraction, location extraction, scene prompts and publishing metadata to Groq. `GROQ_MODEL=openai/gpt-oss-120b` is the default. Set `GROQ_API_KEY` in `.env` and Railway service/worker variables. The operator key is shared across allowlisted chats; their jobs and assets remain separate, but they share the Groq quota.

Images are generated through Replicate's `google/nano-banana`; the canonical visual-tone reference and any scene assets are supplied as ordered image inputs. `prunaai/p-video-2` generates full-quality video from the completed scene image. Set `REPLICATE_API_TOKEN`; missing credentials stop production before media generation starts. Existing assets and saved Replicate prediction journals are reused on resume.

The default Telegram path writes Hindi narration locally after the clips are generated and mixes it into the final edit. P-Video-2 receives a closed-mouth visual direction for this path, so generated video speech cannot conflict with the final narration.

Sources: https://fal.ai/models/fal-ai/flux/schnell ; https://huggingface.co/docs/inference-providers/pricing ; https://console.groq.com/docs/structured-outputs
