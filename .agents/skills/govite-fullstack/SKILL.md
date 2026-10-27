---
name: govite-fullstack
description: Fullstack architecture guide and conventions for Go (Fiber v2) backend and Vite React frontend based on rekanara/govite-fullstack. Use when developing, structuring, or debugging Go Fiber + Vite monorepo apps.
license: MIT
---

# govite-fullstack: Go + Vite Fullstack Starter Guide

Panduan arsitektur dan konvensi pengembangan aplikasi web fullstack menggunakan backend Go (Fiber v2) dan frontend Vite (React + TanStack Router).

# govite-fullstack

Go port of a NestJS starter (monorepo-fullstack). HTTP contract (paths, envelope, cookies, error codes) is kept identical so the admin app works unchanged.

## Layout

- `be/`: one Go module (`govite`). `cmd/api` = server + `migrate` + `seed` subcommands; `cmd/gen` = policy to TS. Feature packages in `internal/<feature>` (`auth`, `account`, `users`, `roles`, `audit`, `settings`, `system`, `announcements`, `notify`, `files`, `integrations`, `rbac`), each split into `domain`, `application`, `infrastructure`, `interface/http` (rules in `be/ARCHITECTURE.md`). Shared: `internal/kernel` (errors, principal, ports), `internal/policy`, `internal/platform/{config,httpx,postgres,crypto,mail,storage,fcm,xport,docs}`. Composition root: `internal/server/wire.go`.
- `fe/`: pnpm workspace, no Turbo. `apps/admin` (package `admin`), `packages/ui` (`@app/ui`), `packages/contracts` (`@app/contracts`, consumed from `src`, no build).
- `docker-compose.yml` at root: infra only (postgres 5434, postgres_test 5436, redis 6380, mailpit 1025/8025, MinIO 9100/9101).

## Commands

- BE (in `be/`): `make lint test`, `make test-e2e` (needs `postgres_test`), `make migrate`, `make seed`, `make gen`, `make dev` (air) / `make run`.
- FE (in `fe/`): `pnpm lint && pnpm typecheck && pnpm test && pnpm build`; single app `pnpm --filter admin <script>`.
- Browser e2e: `scripts/e2e.sh` (Playwright in `fe/apps/e2e`; builds the API, seeds `postgres_test`, runs the admin preview). First run: `pnpm --filter e2e exec playwright install chromium`.
- Smoke: `scripts/smoke.sh` (`API_BASE_URL`, `SUPER_ADMIN_*`; the user must not need 2FA).

## Backend rules

- Fiber v2 with `Immutable: true` (fasthttp buffer reuse). Keep it; don't stash `c.Body()`/`c.Params()` slices otherwise.
- Handlers return errors; `httpx.ErrorHandler` renders the envelope `{data,meta?,error?,status}` with Indonesian `messageInd` (add codes to `httpx/envelope.go`). Domain errors are `kernel.E(kind, CODE, message)` package vars in each feature's `domain`; `httpx.ErrorHandler` maps `kind` to status.
- OpenAPI lives in `internal/platform/docs/openapi.json`; Swagger UI `/api/docs` and raw `/api/docs-json|yaml` are disabled in production. `TestOpenAPICoversRuntimeRoutes` fails when runtime methods/paths drift from the spec.
- Success helpers: `httpx.OK/Created/Page/NoContent/File`. Lists use `httpx.Pagination` + `httpx.NewPageMeta`.
- Validation: `httpx.Body`/`httpx.Query` with `validate` tags (custom tag `password` reads `policy.Security`).
- Routes: public on `api`, self-service on `me` (JWT only), everything else on `rbac.Guarded` whose methods take a required `"resource.action"`, so an undeclared route can't compile; unknown permissions panic at boot.
- Permission catalog and security limits live only in `internal/policy`. After editing: `make gen` (writes `fe/packages/contracts/src/generated.ts`) and `make seed`.
- SQL: add queries in `internal/platform/postgres/queries/*.sql`, run `sqlc generate`; never edit `internal/platform/postgres/store`. Schema changes = new goose file in `internal/platform/postgres/migrations` (embedded in the binary). Tables snake_case, IDs UUIDv7 (`kernel.NewID`).
- Multi-step writes go through `kernel.Tx.Do`. Mutations call `kernel.Auditor.Record(ctx, action, entityType, id, before, after)` explicitly (secrets redacted). The caller is `kernel.PrincipalFrom(ctx)`.
- Role permissions cache in Redis `role-permissions:<roleId>` 60s; call `rbac.Invalidate` on change. Redis optional (nil client = in-memory limiter, no cache).
- Passwords: argon2id PHC, node-argon2 compatible (Nest hashes still verify). 2FA secrets AES-GCM keyed by `REFRESH_TOKEN_PEPPER`.
- Tests: e2e in `internal/server/server_test.go` via `fiber.App.Test` against real Postgres; extend the TRUNCATE list when adding tables.

## Frontend rules

- Admin app: TanStack Router file routes in `src/routes` (thin wiring), pages and API clients in `src/features/<name>`. API base defaults to `/api/v1` (Vite proxy in dev).
- shadcn: `pnpm dlx shadcn@latest add <name> -c apps/admin` from `fe/`; primitives land in `packages/ui`.
- `apps/admin/src/routeTree.gen.ts` is generated; run `pnpm --filter admin exec vite build` after route changes before typecheck.
- New app (e.g. Astro landing): `apps/<name>`, depend on `@app/ui` / `@app/contracts`.


---

# Backend architecture

Each feature in `internal/<feature>` has four layers. Dependencies point inward only.

```
interface/http  ->  application  ->  domain  <-  infrastructure
```

| Layer | Holds | May import | Must not import |
|---|---|---|---|
| `domain` | entities, invariants, error values, ports (interfaces) | `kernel`, `policy`, other features' `domain` | Fiber, `platform/*`, pgx, Redis, `store` |
| `application` | use cases, transactions, audit calls | own `domain`, `kernel`, other features' `application`/`domain` | Fiber, `platform/*`, pgx, Redis, `store` |
| `infrastructure` | adapters for the ports: Postgres repos, crypto, TOTP, mail, FCM, Redis | `domain`, `platform/*`, `store` | `interface` |
| `interface/http` | route wiring, bind + validate, DTOs, status mapping | `application`, `domain`, `platform/httpx`, `rbac` | `infrastructure`, `store` |

Composition happens in one place: `internal/server/wire.go`. Nothing else constructs adapters.

## Rules

- **Errors** are `kernel.E(kind, CODE, message)` values declared in `domain`. `httpx.ErrorHandler` maps `Kind` to a status and renders the envelope. Add new codes to `platform/httpx/envelope.go`.
- **Caller** travels in `context`: `httpx.SetPrincipal` (auth middleware) writes it, use cases read `kernel.PrincipalFrom(ctx)`.
- **Transactions**: use cases call `kernel.Tx.Do(ctx, fn)`. Repositories obtain the transaction-bound queries through `postgres.DB.Q(ctx)`. Nested `Do` joins the outer transaction. Multi-step writes always go through `Do`.
- **Audit**: use cases (or the HTTP handler, when the action name is route-level) call `kernel.Auditor.Record`. Secrets are redacted by `audit/domain.Redact`.
- **Missing rows**: repositories return `postgres.Err(err)`, which maps `pgx.ErrNoRows` to `kernel.ErrNotFound`. Use cases translate it to the feature's own not-found error.
- **Ports only at real seams** (DB, object storage, mail, push, clock-like randomness). No interface with one implementation and no external dependency.
- **Cross-feature use** goes through the other feature's `application` (for example `users` uses `auth` to hash a password and send an invite, `announcements` uses `notify` to broadcast).

## Adding a feature

1. `domain`: entity, rules, errors, `Repository` port.
2. `application`: `Service` with the use cases.
3. `infrastructure`: implement the port with `postgres.DB` and `store` queries (`internal/platform/postgres/queries/*.sql`, then `sqlc generate`).
4. `interface/http`: `Handler{Svc}.Routes(g rbac.Guarded)`; every guarded route names its permission.
5. Wire it in `server/wire.go`, add the permission to `policy`, extend the e2e TRUNCATE list, document the routes in `platform/docs/openapi.json`.

## Checks

- `go list -f '{{.ImportPath}} {{join .Imports " "}}' ./internal/.../domain ./internal/.../application | grep -E "fiber|httpx|postgres|pgx|redis|platform/"` must print nothing.
- `internal/kernel/rules_test.go` covers domain invariants without a database.

