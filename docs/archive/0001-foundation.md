# ADR 0001: Foundation runtime and access boundary

Status: superseded by the outreach-session reset; historical reference only.

## Runtime and persistence

- Next.js / TypeScript web app, synchronous FastAPI / SQLAlchemy domain API, PostgreSQL 17,
  and a separately executable Python worker package. This is a modular monolith.
- Resumatch owns a Compose project (`resumatch`), database container (`resumatch-db-1`),
  and named volume (`resumatch_postgres_data`). Bind only to loopback, host port 55432.
  This coexists with Pixis FinOps and a host PostgreSQL on 5432.
- Alembic owns schema changes. Startup never creates tables implicitly. UV and npm lockfiles
  pin dependencies. Run commands from the repository root unless stated otherwise.

## Authentication

- Local email/password accounts, Argon2id password hashes, and random 256-bit opaque session
  tokens. Store only SHA-256 token hashes in PostgreSQL. Sessions expire after seven days,
  rotate on login, and are revoked on logout. No browser-provided user ID establishes identity.
- Browser traffic uses one origin: Next.js proxies `/api/*` to the private API. Session cookies
  are HttpOnly, SameSite=Lax, host-only, and Secure when `COOKIE_SECURE=true`. No localStorage
  authentication. API responses are `no-store`.
- Every state-changing browser endpoint requires an exact configured `Origin`, including login
  and registration. Allow `WEB_ORIGIN` plus an explicit JSON list in `WEB_ADDITIONAL_ORIGINS`.
  The local example allows both `localhost:3000` and `127.0.0.1:3000`; other hosts/ports do not
  inherit trust. No CORS wildcard. Direct API clients must supply an allowed origin.
- Private profile reads/writes derive their owner from the session. There is no arbitrary-owner
  profile endpoint. Reject unknown input fields, including injected user IDs. Version checks
  prevent lost profile edits. Future joins must scope every private side to the authenticated user.
- API-level ownership is the current enforcement boundary. There are no RLS policies yet;
  the database is private to trusted API/worker processes and must never be browser-accessible.

## Queue and storage decisions

- Use **Procrastinate**, a maintained PostgreSQL-backed queue, for milestone 2 ingestion.
  Install its schema with versioned integration changes when the first real handler is added.
  It will own claiming, locks, retries, and worker recovery; no in-memory background collection.
  The current worker entrypoint only checks connectivity, and is not a working task runner.
- Use an owner-authorized storage service interface with a **local filesystem adapter** for
  development and S3-compatible adapter for deployment in milestone 4. Store opaque relative
  keys/hashes in PostgreSQL, immutable bytes outside it, and authorize downloads via the API.
  Do not expose the local directory as static content. No unused document tables or adapter yet.

## Deployment assumptions and limits

This foundation targets a single developer's local machine. Before public beta, configure HTTPS
and secure cookies, disable open registration as appropriate, add trusted-edge login/registration
rate limiting, account recovery and email verification, session cleanup, production secrets,
backups, and a restricted database role. No email verification or password recovery is implemented
yet. No external auth, paid service, scraper, or LLM credential is required locally.

Never log passwords or raw session tokens. Tests use a separate PostgreSQL database ending in
`_test`, execute real migrations, and check two identities and session revocation against it.
