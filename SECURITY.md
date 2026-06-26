# Security and Privacy

This repository is intended to contain source code only.

Do not commit:

- Real `.env` files or API keys.
- Local SQLite databases, saves, turn logs, or exported game data.
- User-uploaded avatars or other private media.
- Virtual environments, dependency folders, build outputs, or cache files.

Use `backend/.env.example` as the public configuration template, then create a private `backend/.env` locally.

If a secret is accidentally committed, rotate the secret immediately and remove it from git history before making the repository public.
