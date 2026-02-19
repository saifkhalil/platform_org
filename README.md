# Platform Org Suite (Django 5)

Platform Org is a tenant-aware operating platform for micro-enterprise contract management, SLA monitoring, VAM tracking, and KPI governance.

## Stack
- Django 5 + DRF
- PostgreSQL
- Redis
- Celery (worker + beat)
- Entra ID token validation
- Bootstrap template UI + REST API

## Key Features
- Tenant isolation via `request.tenant` middleware (subdomain, `X-Tenant`, Entra claims, user membership fallback).
- Tenant-scoped domain entities (MEs, contracts, SLA templates, service requests, breaches, VAM agreements, KPIs).
- SLA breach monitoring task with Teams/email notification hooks.
- Role-aware API and write-guarded template views.

## Local Run
```bash
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

## Docker Run
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api uv run python manage.py migrate
docker compose exec api uv run python manage.py createsuperuser
```

## Endpoints
- Dashboard: `http://localhost:8000/`
- API root: `http://localhost:8000/api/`
- API docs: `http://localhost:8000/api/docs/`
- Health: `http://localhost:8000/healthz`
