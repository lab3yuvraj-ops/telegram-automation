# Nightfall SaaS architecture

## Customer flow

Signup → sign in → connect a personal Gemini API key → title → durable production queue → private film library.
New users never inherit the administrator's key. Each live job receives an encrypted snapshot of its owner's key.
Replacing an account key affects new jobs; outstanding jobs retain their original key so saved Google operations remain accessible.

## Hosted components

- FastAPI web service: authentication, ownership checks, API-key onboarding, job submission, private downloads.
- PostgreSQL: users, sessions, encrypted keys, queue, script history, artifact index.
- Private Railway S3 bucket: reference images, JSON checkpoints, audio, video and export packages. Downloads pass through authenticated ownership checks; no public bucket URLs.
- Separate worker service: two replicas, two job slots per replica. Four different customers can render concurrently; additional customers wait in the durable queue.
- PostgreSQL row locks prevent duplicate claims. Per-customer advisory locks allow one running job per customer and up to three active/queued jobs per customer.
- Heartbeats identify interrupted workers. Interrupted jobs pause for reconciliation instead of blindly submitting paid requests again.

Hundreds of accounts can use the dashboard and submit jobs. Hundreds of simultaneous video renders require additional funded worker capacity and suitable provider quotas. The current deployment does not promise 200 simultaneous renders.

## Writing strategy

`app/story_engine.py` implements PDF prompts 1 and 3, and Chapter 1's sequence:

1. Method B expands the supplied title into a hook, category, entity, brief and emotional core.
2. A six-act blueprint fixes hook, rupture, escalation, truth/backstory, climax and resolution/twist.
3. Eight 7.5-second spoken scenes target the course's roughly 150 words/minute (135–150 target; 120–160 allowed).
4. An independent model critique checks ten requirements against actual spoken evidence. Failed drafts receive up to two revisions.
5. Exact and high textual similarity checks plus model comparison against up to 30 recent scripts from the same account discourage repeated plots. A fresh variation token is saved for every new production; resume preserves it.
6. A fingerprint locks spoken text before character/background extraction. New productions create new scripts; resume retains the original script.

Long-form timing is explicitly adapted: scene 1 hook, scene 2 rupture, scenes 3–5 escalation, scene 6 truth, scene 7 climax, scene 8 twist. Literal 60–90-second hooks cannot fit a one-minute film. The course's manual choice of hooks becomes automatic for title-only input.

## Verification and limits

- 25 local tests passed, covering auth, ownership, keys, signup, per-user queues, script structure, duplicate detection and the earlier media pipeline.
- Hosted PostgreSQL diagnostic: 200 tenants, 200 distinct job claims, 20 parallel queue threads, 200 cross-account checks, 200 simultaneous dashboard requests; no Google calls. This uses an isolated disposable schema, not production accounts.
- Existing SQLite data and films migrated to PostgreSQL/private storage without deleting the old volume.
- Distributed worker completed a 60-second demo render. Demo cards do not establish AI footage quality.
- The first live writing calibration was correctly rejected for missing audible hook/climax/twist elements. Instructions were tightened. The next attempt stopped on Google 503, then the key's daily free-tier text quota. A successful revised live script and complete paid video calibration remain outstanding.
- Text novelty and visual consistency checks are heuristic, not guarantees. Final editorial review remains valuable.
- Subscription charging, email verification, password recovery, team seats, storage quotas, self-service account deletion and automated backups are not included. This is a working SaaS foundation, not a finished commercial billing product.

## Operations

Keep `APP_ENCRYPTION_KEY` stable and back it up separately. Back up PostgreSQL and private objects. Restrict production environment variables to operators.
Configure `DATABASE_URL`, `S3_BUCKET`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and `S3_REGION` on web and workers.
Set `APP_ROLE=worker` and start `python -m app.worker` on workers; use ephemeral `DATA_DIR=/tmp/nightfall`. Completed local render caches are removed only after uploads succeed.
The web service retains `/data` for the legacy migration. No new production files rely on that volume in distributed mode.
Raise worker replicas gradually while observing CPU, memory, database connections, queue time and actual generation costs.
