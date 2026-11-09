# AI Career Mentor

## Initial installation

Use Python 3.11+ and MySQL 8.x (InnoDB, `utf8mb4`). The existing application
dependencies are listed in `requirements.txt`; no extra package is required for
catalog data or administration.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env` to your MySQL database, including
`?charset=utf8mb4`. Generate a private random `SECRET_KEY` with
`python -c "import secrets; print(secrets.token_urlsafe(32))"` and set it in
`.env`. Set `CORS_ALLOWED_ORIGINS` to a JSON list of exact frontend origins
(for example `["https://your-frontend.example"]`) when the frontend is hosted on
a different origin; wildcard origins are not accepted. Never commit `.env`.

The API uses bcrypt-hashed passwords and short-lived HS256 Bearer tokens.
Public registration always creates a student; Admin rights are checked against
the current database role on every request. API successes and errors use a
consistent JSON envelope, retaining `detail` on errors for existing clients.
In production, `SECRET_KEY` must be explicitly configured.

Run the database migration; it creates the learning-resource table and seeds
career categories, roles, role-skill requirements, skills, and curated learning
links. Then create the administrator. The command prompts for the email and
reads the password without echoing it, so do not put the password in `.env` or
on the command line.

```powershell
python -m alembic upgrade head
python -m app.bootstrap_admin
python -m uvicorn app.main:app --reload
```

Choose an Admin password of 8–72 UTF-8 bytes and confirm it at the prompt. The
bootstrap command is safe to repeat for an existing Admin account; it refuses
to promote an existing student account.

## Data discovery and administration

- `/` and `/explore`: browse career paths, required skills, and learning links.
- `/api/v1/catalog/categories`, `/roles`, `/skills`, `/resources`: public,
  read-only catalog APIs.
- `/api/v1/admin/catalog`: Admin-only catalog overview.
- `/api/v1/admin/career-categories`, `/career-roles`, `/skills`, `/resources`:
  Admin-only create, update, and delete APIs. Interactive API documentation is
  at `/docs`; authenticate with an Admin access token to use these endpoints.

Registering through the public auth API always creates a student account.
Admin access is granted only through the bootstrap command or an existing
administrator process.
