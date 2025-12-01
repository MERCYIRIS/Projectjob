# Copilot / AI assistant instructions for JobBoard

This file gives focused, actionable guidance to an AI coding agent working on this repository.

Summary
- Single-file Flask app located at `app.py` (primary runtime). Small supplemental snippets in `app_auth_snippet.py`.
- Uses SQLite DB `jobs.db` created automatically in the project root by `init_db()` when first run.
- Templates live in `templates/` (Jinja) and static assets in `static/`.

Key entrypoints & routes
- `app.py` - main application and route definitions. Run with `python app.py` (development mode, debug=True).
- Important routes to reference: `/`, `/add`, `/job/<id>`, `/register`, `/login`, `/logout`,
  `/reset_password_request`, `/reset_password/<token>`, `/profile/<username>`, `/api/jobs`.

Database & helpers
- DB path: configured via `app.config['DATABASE']` -> `jobs.db` (SQLite).
- Use the provided helpers: `get_db()`, `query_db(query, args, one=False)` and `execute_db(query, args)`.
  - These ensure `row_factory` and connection lifecycle are correct (closed on teardown).
- Schema created in `init_db()` inside `app.py`. Do not change schema without adjusting `init_db()` and any code that reads/writes tables.

Auth, sessions & tokens
- Sessions: `session` stores `user_id`, `username`, `is_employer`. Use `current_user()` helper and `inject_user()` context processor to access user in templates.
- Passwords hashed with `werkzeug.security.generate_password_hash` and verified with `check_password_hash`.
- Password reset tokens use `itsdangerous.URLSafeTimedSerializer` and `send_reset_email()` prints a reset link to console (no SMTP configured).
- Environment: set `FLASK_SECRET` env var to override the default `app.secret_key` (default = `change-this-secret`).

Templates / form fields (concrete examples)
- `templates/add_job.html`: expects `title`, `description`, `tags`, `salary` fields in POST form.
- `respond` route expects `text` and optional `contact` form keys when posting to `/respond/<job_id>`.
- Registration/login forms use Flask-WTF `RegistrationForm`/`LoginForm` defined in `app.py` (fields: `username`, `password`, `password2`, `email`, `employer`, `remember`).

Developer workflow & commands
- Install deps: `pip install -r requirements.txt`
- Run dev server: `python app.py` (listens on 0.0.0.0:5000 by default, debug=True). On Windows PowerShell you can optionally set secret before running:
  - `$env:FLASK_SECRET="your-secret"; python app.py`
- Database auto-creation: on first run `init_db()` will create `jobs.db` and insert sample users:
  - `employer1` / `password123` (is_employer=1)
  - `worker1` / `password123` (is_employer=0)

Conventions & patterns specific to this repo
- Single-file app pattern: keep route logic in `app.py`. If extracting features, maintain the same helpers (`get_db`, `query_db`, `execute_db`, `current_user`) to avoid breaking code.
- Templates assume `user` is available via context processor. Prefer `current_user()` for view logic and `user` in templates.
- Use Flask-WTF forms (already in `app.py`) instead of raw request parsing when adding form-backed pages.
- For DB writes/reads, prefer `execute_db` / `query_db` to preserve the connection context and commit behavior.

API & integration
- Public API endpoint: `/api/jobs` returns JSON list of jobs. Keep JSON shapes simple (dict rows from SQLite).
- Password reset: link is printed to console for dev—do not expect real email sending unless SMTP is added.

Security notes for contributors
- Change the default secret in production using `FLASK_SECRET`.
- Be mindful of SQL injection vectors; code currently uses parameterized queries (good). Keep using `?` placeholders.

When editing files
- If you modify DB schema or column names, update `init_db()` and all SQL queries in `app.py` accordingly.
- Keep templates field names consistent with route expectations (`title`, `description`, `tags`, `salary`, `text`, `contact`).

If you need more
- Ask for clarification about where to split `app.py` into modules, or for adding migrations/tests.
- If you want, I can add a `README.md` or a small `manage.py` CLI to run DB commands and tests.

---
If any part of this summary is unclear or you want additional details (tests, CI, or refactor suggestions), tell me what to expand.
