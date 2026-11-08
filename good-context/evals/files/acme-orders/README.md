# Acme Orders

Order management backend: an HTTP API (`services/api`) and a background worker (`services/worker`).

## Getting started

Requires Node 20 (see `.nvmrc`) and pnpm 9.

```bash
pnpm install
cp .env.example .env
docker compose up -d postgres redis
pnpm dev
```

## Scripts

| Command | What it does |
|---|---|
| `pnpm build` | Type-check and build all services |
| `pnpm test` | Run all unit tests (Vitest) |
| `pnpm lint:js` | ESLint across the monorepo |
| `pnpm format` | Prettier write |

Deployments run from GitLab CI: `deploy:staging` runs on every merge to `main`; `deploy:production` is a manual job.
