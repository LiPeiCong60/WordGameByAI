# Security and Privacy

This repository is intended to contain source code only.

Do not commit:

- Real `.env` files or API keys.
- Local SQLite databases, saves, turn logs, or exported game data.
- User-uploaded avatars or other private media.
- Virtual environments, dependency folders, build outputs, or cache files.

Use `backend/.env.example` as the public configuration template, then create a private `backend/.env` locally.

If a secret is accidentally committed, rotate the secret immediately and remove it from git history before making the repository public.

## Runtime Data

The application stores user accounts, bearer token hashes, game saves, characters, lore, turns, management proposals, templates, and captcha challenges in the configured database. Local development uses `backend/narrative_agent.db`, which is ignored by Git.

User-uploaded files are stored under `backend/uploads/`, which is also ignored except for placeholder directories.

## Public Deployment Notes

- Do not expose the FastAPI port directly to the internet; put Nginx/Caddy in front of it.
- Set `CORS_ALLOW_ORIGINS` to the exact production frontend origin.
- Keep `OPENAI_API_KEY` only in server environment variables or a private `.env`.
- Rotate any key that has ever appeared in chat logs, screenshots, shell history, or Git history.
- Use HTTPS for public deployments.
- Login and registration both require captcha. Consider replacing the lightweight built-in captcha with Turnstile/hCaptcha/reCAPTCHA before opening registration publicly.
- Keep per-user message quotas and rate limits enabled to control model cost and abuse.
