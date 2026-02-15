# Platform Org Suite v2 (Django + React Fluent UI)

Includes:
- Backend: Django 5 + DRF + JWT, row-level RBAC, audit log, seed command, integration stubs, health endpoint
- Frontend: React (Vite) + Fluent UI with routing, login page, protected routes, list pages (ME, Contracts, VAM, SLA, KPI), audit page placeholder
- Docker: Postgres + Redis + Celery (worker/beat) + API + Frontend

## Run (Docker)
```bash
cp backend/.env.example backend/.env
docker compose up --build -d
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_platform_org
docker compose exec api python manage.py createsuperuser
```
- UI: http://localhost:5173
- API: http://localhost:8000/api/
- Docs: http://localhost:8000/api/docs/
- Health: http://localhost:8000/healthz


## v4
- Multi-tenancy via X-Tenant header
- SLA monitoring engine (Celery Beat)
- VAM autonomy scoring + tranche auto-release (baseline)
- Entra ID (Azure AD) Bearer token authentication
- K8s/Helm/Traefik blueprints


## v5 (2026-01-15)
- Strict Entra ID SSO validation (issuer/audience)
- Tenant isolation from Entra claims (tid/groups) + dev X-Tenant fallback
- SLA Breach alerts via Teams webhook + SLA breaches UI page
- Helm chart: configmap/secret/HPA templates


## Docker fix
- Backend venv moved to /opt/venv to avoid being shadowed by volume mounts (fixes 'No module named uvicorn').
