# Security

Shelfkeep is a **single-user, self-hosted** app. Treat the machine that runs
it as the security boundary.

## Default login

`.env.example` and Compose defaults use:

- username: `admin`
- password: `changeme`

**Change `SHELFKEEP_PASSWORD` before you expose the process on a network.**
The app logs a warning at boot if the default password is still in use.

## Session secret

`SESSION_SECRET` signs the `shelfkeep_session` cookie.

- Leave it **blank** in `.env` (the documented Compose path). The app generates
  a unique key and persists it under `DATA_DIR` (`.session_secret`, mode `0600`).
- Documented placeholders (`change-this-session-secret`,
  `replace-with-a-long-random-string`, or empty) are **never** used to sign
  cookies.
- Do not commit a real secret. `.env` is gitignored; `.env.example` must stay
  free of live credentials.

## Secrets in this repository

Do not add API keys, passwords, cookies, or private keys to the tree.

- Book lookup uses public [Open Library](https://openlibrary.org) APIs. There
  is no Shelfkeep cloud account and no retailer API key.
- Uploads (covers, item photos, receipts) belong in Docker volumes or `DATA_DIR`,
  not in git.

If you find a secret in a commit, rotate it and open a security report.

## Reporting a vulnerability

Please **do not** file a public GitHub issue for an exploitable bug.

1. Use [GitHub private vulnerability reporting](https://github.com/Jstaud/shelfkeep/security/advisories/new)
   if it is enabled on this repository, **or**
2. Email the maintainer at the address on their [GitHub profile](https://github.com/Jstaud).

Include the version (`GET /healthz` returns `version`), what you ran, and a
minimal reproduction. You should hear back within a few days.

## Supported versions

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |
| < 1.0 | No |

## Deployment notes

- Bind the HTTP server as Compose does (`0.0.0.0:8080` inside the container,
  published to your host). The packaged `shelfkeep` binary binds
  `127.0.0.1:8080` unless you pass `--host`. Put TLS in front if you leave
  localhost.
- Set `SESSION_HTTPS_ONLY=true` when you terminate TLS.
- Postgres credentials in Compose are for the local database. Change
  `POSTGRES_PASSWORD` if the database port is reachable beyond the Compose
  network.
- Official image: `ghcr.io/jstaud/shelfkeep` (see the README). Compose
  `up --build` still builds from the Dockerfile and does not require a
  registry. Make the GHCR package public after the first push if pulls
  should work without a GitHub login.
