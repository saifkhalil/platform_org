# Platform Org Suite - System Architecture

## Overview

Platform Org Suite is a multi-tenant enterprise platform for managing micro-enterprises (ME), contracts, services, SLA monitoring, and Value-Added Management (VAM) autonomy scoring. Built on Django 5 with React frontend, it implements the Rendanheyi/Haier organizational model with strict tenant isolation and Azure Entra ID authentication.

**Version:** 0.3.0 (v5 - 2026-01-15)

---

## Architecture Layers

### 1. Presentation Layer

#### Frontend (React + Fluent UI)
- **Technology Stack:**
  - React with Vite build system
  - Microsoft Fluent UI component library
  - Client-side routing with protected routes
  - JWT-based authentication

- **Key Features:**
  - Login page with Entra ID integration
  - Protected routes requiring authentication
  - List pages: Micro Enterprises, Contracts, VAM, SLA, KPI
  - Audit log viewer
  - SLA breach monitoring dashboard

- **Deployment:**
  - Served via static file hosting
  - Accessible at `http://localhost:5173` (dev)
  - Production: Kubernetes ingress with Traefik

#### Backend API (Django REST Framework)
- **Technology Stack:**
  - Django 5.x
  - Django REST Framework (DRF) 3.15+
  - drf-spectacular for OpenAPI/Swagger documentation

- **API Endpoints:**
  - `/api/` - Main API root
  - `/api/docs/` - Interactive API documentation (Swagger)
  - `/healthz` - Health check endpoint
  - `/admin/` - Django admin interface

- **Authentication:**
  - Entra ID Bearer token (primary)
  - JWT tokens (djangorestframework-simplejwt)
  - Automatic user provisioning from Entra ID claims

---

### 2. Application Layer

#### Core Django Apps

##### **platform_org.core**
Main business logic for micro-enterprises, contracts, and services.

**Models:**
- `MicroEnterprise` - Core organizational unit with autonomy levels (HIGH/STANDARD/RESTRICTED)
- `MicroEnterpriseType` - Classification of MEs
- `MicroEnterpriseStatus` - Lifecycle status tracking
- `MEOwner` - Many-to-many relationship between users and MEs with roles
- `MEService` - Services provided by MEs (supports hierarchical sub-services)
- `MEContract` - Contracts between provider and consumer MEs
- `ContractService` - Many-to-many through model linking contracts to services with billing details
- `ContractStatus` - Contract lifecycle states
- `SLATemplate` - Reusable SLA definitions (response time, resolution time, availability)
- `ServiceSLACost` - Cost matrix for services at different SLA levels
- `VAMAgreement` - Value-Added Management agreements
- `MEKPI` - Key Performance Indicators for MEs

**Key Features:**
- Row-level tenant isolation on all models
- Audit logging integration
- VAM autonomy scoring engine
- Service hierarchy support (parent-child relationships)
- Flexible billing types (QUANTITY, PERIOD)

##### **platform_org.sla**
SLA monitoring and breach detection system.

**Models:**
- `ServiceRequest` - Tracks service requests from external systems (Jitbit, Jira, Manual)
- `SLABreachEvent` - Records SLA violations (RESPONSE, RESOLUTION types)

**Background Tasks:**
- `check_sla_breaches` - Runs every 5 minutes via Celery Beat
  - Monitors open/in-progress service requests
  - Detects response time breaches (no first response)
  - Detects resolution time breaches (not resolved)
  - Sends Teams webhook notifications on new breaches

**Integration Points:**
- Jitbit ticketing system
- Jira issue tracking
- Manual entry support

##### **platform_org.tenancy**
Multi-tenancy infrastructure with Entra ID integration.

**Models:**
- `Tenant` - Organization/tenant entity
  - `code` - Unique slug identifier
  - `entra_tenant_id` - Azure AD tenant ID mapping
  - `entra_group_id` - Azure AD group ID mapping
  - `is_active` - Soft delete flag
- `TenantUser` - User-tenant membership with roles
  - Roles: PLATFORM_ADMIN, TENANT_ADMIN, MEMBER

**Middleware:**
- `TenantMiddleware` - Request-level tenant resolution
  - Production: Resolves from Entra ID claims (tid/groups)
  - Development: Falls back to X-Tenant header
  - Auto-creates "default" tenant in DEBUG mode

##### **platform_org.audit**
Comprehensive audit logging system.

**Models:**
- `AuditEvent` - Immutable audit trail
  - `actor` - User who performed the action
  - `action` - Action type (CREATE, UPDATE, DELETE, etc.)
  - `entity_type` - Model name
  - `entity_id` - Primary key of affected entity
  - `summary` - Human-readable description
  - `payload` - JSON field for detailed change data
  - Indexed on entity_type/entity_id and created_at

**Features:**
- Automatic logging via model signals
- Manual logging via `log_event()` helper
- Queryable audit trail for compliance

##### **platform_org.accounts**
User authentication and account management.

##### **platform_org.integrations**
External system integration tasks and connectors.

**Background Tasks:**
- Integration with external ticketing systems
- Data synchronization tasks

##### **platform_org.health**
System health monitoring endpoints.

**Endpoints:**
- `/healthz` - Liveness/readiness probe for Kubernetes

---

### 3. Security Layer

#### Authentication System

##### **Entra ID (Azure AD) Authentication**
Primary authentication mechanism for production.

**Implementation:** `platform_org.core.authentication.EntraIDAuthentication`

**Features:**
- JWT signature verification using JWKS (JSON Web Key Set)
- Issuer validation against `ENTRA_ALLOWED_ISSUER`
- Audience validation against `ENTRA_CLIENT_ID`
- Automatic user provisioning from token claims
- Claims extraction for tenant resolution

**Token Validation Flow:**
1. Extract Bearer token from Authorization header
2. Decode unverified token to get issuer
3. Fetch JWKS from Microsoft's discovery endpoint
4. Verify signature using public key
5. Validate issuer and audience
6. Extract user identity (preferred_username/upn/email)
7. Get or create Django user
8. Attach claims to `request.entra_claims`

**Configuration:**
- `ENTRA_TENANT_ID` - Azure AD tenant ID
- `ENTRA_CLIENT_ID` - Application (client) ID
- `ENTRA_ALLOWED_ISSUER` - Expected token issuer URL

##### **JWT Authentication**
Fallback authentication for development and service-to-service communication.

**Implementation:** `djangorestframework-simplejwt`

**Configuration:**
- Access token lifetime: 60 minutes (configurable)
- Refresh token lifetime: 7 days (configurable)

#### Authorization System

##### **Row-Level Tenant Isolation**
Every model includes a `tenant` foreign key enforcing data isolation.

**Enforcement Points:**
- Middleware sets `request.tenant` on every request
- Views filter querysets by `request.tenant`
- Serializers validate tenant ownership
- Admin interface respects tenant boundaries

##### **Role-Based Access Control (RBAC)**
Implemented via `TenantUser.role` field.

**Roles:**
- **PLATFORM_ADMIN** - Cross-tenant administration
- **TENANT_ADMIN** - Full access within tenant
- **MEMBER** - Standard user access

**Permission Classes:**
- Custom DRF permission classes in `platform_org.core.permissions`
- Row-level permission checks
- Action-based permissions (view, create, update, delete)

#### Security Middleware Stack
1. `SecurityMiddleware` - Django security headers
2. `WhiteNoiseMiddleware` - Static file serving with security headers
3. `CorsMiddleware` - CORS policy enforcement
4. `TenantMiddleware` - Tenant resolution and isolation
5. `AuthenticationMiddleware` - User authentication
6. `CsrfViewMiddleware` - CSRF protection

---

### 4. Business Logic Layer

#### VAM (Value-Added Management) Engine

**Implementation:** `platform_org.core.vam_engine.compute_autonomy_scores`

**Execution:** Daily via Celery Beat (86400 seconds)

**Autonomy Scoring Algorithm:**
```
score = max(0, min(100, 100 - (breaches × 10) + (kpi_hit × 5)))

Autonomy Levels:
- score >= 80: HIGH
- score >= 50: STANDARD
- score < 50: RESTRICTED
```

**Inputs:**
- SLA breach count for ME's provided services
- KPI achievement rate (actual_value >= target_value)

**Outputs:**
- Updated `MicroEnterprise.autonomy_level`
- Automatic VAM tranche release (score >= 70)

**Tranche Auto-Release Policy:**
- Pending tranches released when autonomy score >= 70
- Status changed from PENDING to RELEASED
- Release date recorded

#### SLA Monitoring Engine

**Implementation:** `platform_org.sla.tasks.check_sla_breaches`

**Execution:** Every 5 minutes via Celery Beat (300 seconds)

**Monitoring Logic:**
1. Query all OPEN/IN_PROGRESS service requests
2. For each request with SLA template:
   - **Response Time Check:**
     - If no first_response_at and elapsed > response_time_hours
     - Create RESPONSE breach event
   - **Resolution Time Check:**
     - If no resolved_at and elapsed > resolution_time_hours
     - Create RESOLUTION breach event
3. Send Teams webhook notification for new breaches
4. Prevent duplicate breach events (get_or_create)

**Notification Integration:**
- Microsoft Teams webhook via `platform_org.core.notifications.send_teams_webhook`
- Configurable via `TEAMS_WEBHOOK_URL` environment variable

---

### 5. Data Layer

#### Database Architecture

##### **PostgreSQL 16**
Primary relational database.

**Schema Design:**
- Multi-tenant with tenant_id on all tables
- Composite unique constraints for tenant isolation
- Foreign key relationships with CASCADE/PROTECT policies
- Indexed fields for performance (tenant_id, created_at, status fields)

**Key Relationships:**
- MicroEnterprise ↔ MEOwner ↔ User (many-to-many)
- MicroEnterprise → MEService (one-to-many, hierarchical)
- MEContract ↔ ContractService ↔ MEService (many-to-many)
- MEContract → ServiceRequest → SLABreachEvent (one-to-many chains)
- MicroEnterprise → VAMAgreement → VAMTranche (one-to-many chains)

**Migrations:**
- Django migrations in each app's `migrations/` directory
- Version controlled migration history
- Seed data via `seed_platform_org` management command

##### **Redis 7**
In-memory data store for caching and message brokering.

**Use Cases:**
- Celery message broker (task queue)
- Celery result backend (task results)
- Session storage (optional)
- Cache backend (optional)

**Configuration:**
- `REDIS_URL` - Connection string
- `CELERY_BROKER_URL` - Task queue endpoint
- `CELERY_RESULT_BACKEND` - Result storage endpoint

#### Data Models Summary

**Core Entities:**
- 13 models in `platform_org.core`
- 2 models in `platform_org.sla`
- 2 models in `platform_org.tenancy`
- 1 model in `platform_org.audit`

**Tenant Isolation:**
- All business models include `tenant` ForeignKey
- Enforced at middleware, ORM, and serializer levels

**Audit Trail:**
- All models inherit from `TimeStampedModel` (created_at, updated_at)
- Critical operations logged to `AuditEvent`

---

### 6. Integration Layer

#### External System Integrations

##### **Microsoft Teams**
- Webhook-based notifications
- SLA breach alerts
- Configurable via `TEAMS_WEBHOOK_URL`

##### **Ticketing Systems**
- **Jitbit** - Service request import
- **Jira** - Issue tracking integration
- External ID mapping in `ServiceRequest.external_id`

##### **Azure Entra ID (Azure AD)**
- SSO authentication
- User provisioning
- Tenant/group mapping
- JWKS-based token validation

#### API Integration Points

**REST API:**
- OpenAPI 3.0 specification via drf-spectacular
- JSON request/response format
- Pagination (limit/offset, 50 items per page)
- CORS support for frontend integration

**Webhook Endpoints:**
- Incoming webhooks for external system events
- Outgoing webhooks for notifications (Teams)

---

### 7. Background Processing Layer

#### Celery Architecture

##### **Celery Worker**
Processes asynchronous tasks.

**Configuration:**
- Broker: Redis
- Result backend: Redis
- Serialization: JSON
- Timezone: Asia/Baghdad
- Concurrency: Auto-detected (CPU cores)

**Task Types:**
- SLA monitoring tasks
- VAM autonomy computation
- Integration synchronization
- Notification delivery

##### **Celery Beat**
Scheduled task execution (cron-like).

**Schedule:**
```python
CELERY_BEAT_SCHEDULE = {
    "sla-check-every-5-min": {
        "task": "platform_org.sla.tasks.check_sla_breaches",
        "schedule": 300.0,  # 5 minutes
    },
    "vam-autonomy-daily": {
        "task": "platform_org.core.vam_engine.compute_autonomy_scores",
        "schedule": 86400.0,  # 24 hours
    },
}
```

**Monitoring:**
- Task execution logs
- Result tracking in Redis
- Error handling and retry logic

---

### 8. Deployment Layer

#### Development Environment

##### **Docker Compose**
Local development stack.

**Services:**
- **api** - Django application (Gunicorn + Uvicorn workers)
  - Port: 8000
  - Workers: 3
  - Timeout: 120s
  - Auto-migration on startup
- **worker** - Celery worker
- **beat** - Celery beat scheduler
- **db** - PostgreSQL 16 Alpine
  - Port: 5432
  - Persistent volume: pgdata
- **redis** - Redis 7 Alpine
  - Port: 6379

**Startup Sequence:**
```bash
docker compose up --build -d
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_platform_org
docker compose exec api python manage.py createsuperuser
```

**Access Points:**
- UI: http://localhost:5173
- API: http://localhost:8000/api/
- Docs: http://localhost:8000/api/docs/
- Health: http://localhost:8000/healthz

#### Production Environment

##### **Kubernetes Deployment**

**Namespace:** `platform-org` (defined in `deploy/k8s/namespace.yaml`)

**Workloads:**
- **API Deployment** (`deploy/k8s/api-deployment.yaml`)
  - Replicas: 2 (configurable via Helm)
  - Container: Gunicorn + Uvicorn ASGI server
  - Health checks: liveness and readiness probes on `/healthz`
  - Resource limits and requests
  - Environment variables from ConfigMap and Secrets

- **Worker Deployment** (Helm-managed)
  - Replicas: 1 (configurable)
  - Celery worker process
  - Shared configuration with API

- **Beat Deployment** (Helm-managed)
  - Replicas: 1 (singleton)
  - Celery beat scheduler
  - Shared configuration with API

**Services:**
- **API Service** (`deploy/k8s/api-service.yaml`)
  - Type: ClusterIP
  - Port: 8000
  - Selector: app=platform-org-api

**Ingress:**
- **IngressRoute** (Traefik CRD)
  - API host: `api.example.com`
  - Web host: `app.example.com`
  - TLS termination
  - Path-based routing

**Horizontal Pod Autoscaler (HPA):**
- Target: API deployment
- Metrics: CPU utilization
- Min replicas: 2
- Max replicas: 10 (configurable)

##### **Helm Chart**

**Chart Location:** `deploy/helm/platform-org/`

**Templates:**
- `configmap.yaml` - Non-sensitive configuration
- `secret.yaml` - Sensitive credentials (base64 encoded)
- `deployment-api.yaml` - API deployment
- `service-api.yaml` - API service
- `ingressroute.yaml` - Traefik ingress
- `hpa-api.yaml` - Horizontal pod autoscaler

**Values (`values.yaml`):**
```yaml
image:
  api: your-registry/platform-org-api:latest
  web: your-registry/platform-org-web:latest

replicaCount:
  api: 2
  worker: 1

ingress:
  enabled: true
  className: traefik
  apiHost: api.example.com
  webHost: app.example.com
  tls: true

secrets:
  djangoSecretKey: "change-me"
  databaseUrl: "postgresql://user:pass@host:5432/db"
  redisUrl: "redis://host:6379/0"
  entraTenantId: ""
  entraClientId: ""
  entraAllowedIssuer: ""
  teamsWebhookUrl: ""
```

**Deployment Commands:**
```bash
helm install platform-org ./deploy/helm/platform-org \
  --namespace platform-org \
  --create-namespace \
  --values custom-values.yaml
```

##### **Container Image**

**Dockerfile:** `docker/Dockerfile`

**Build Strategy:**
- Base image: Python 3.12+
- Package manager: uv (fast Python package installer)
- Virtual environment: `/opt/venv` (avoids volume mount shadowing)
- Static files: Collected and served via WhiteNoise
- ASGI server: Gunicorn with Uvicorn workers

**Image Layers:**
1. System dependencies
2. Python dependencies (uv install)
3. Application code
4. Static file collection
5. Entrypoint configuration

---

### 9. Configuration Management

#### Environment Variables

**Django Core:**
- `DJANGO_SECRET_KEY` - Cryptographic signing key
- `DJANGO_DEBUG` - Debug mode (False in production)
- `DJANGO_ALLOWED_HOSTS` - Comma-separated host list

**Database:**
- `DATABASE_URL` - PostgreSQL connection string
  - Format: `postgresql://user:pass@host:port/dbname`

**Redis/Celery:**
- `REDIS_URL` - Redis connection string
- `CELERY_BROKER_URL` - Task queue broker (defaults to REDIS_URL)
- `CELERY_RESULT_BACKEND` - Result storage (defaults to REDIS_URL)

**Authentication:**
- `ACCESS_TOKEN_LIFETIME_MINUTES` - JWT access token TTL (default: 60)
- `REFRESH_TOKEN_LIFETIME_DAYS` - JWT refresh token TTL (default: 7)
- `ENTRA_TENANT_ID` - Azure AD tenant ID
- `ENTRA_CLIENT_ID` - Azure AD application ID
- `ENTRA_ALLOWED_ISSUER` - Expected token issuer URL

**Integrations:**
- `TEAMS_WEBHOOK_URL` - Microsoft Teams webhook for notifications

**Frontend:**
- `CORS_ALLOWED_ORIGINS` - Comma-separated list of allowed origins

#### Configuration Files

**Django Settings:** `config/settings.py`
- Environment-based configuration via django-environ
- Middleware stack definition
- Installed apps registration
- REST framework configuration
- Celery beat schedule
- Database and cache configuration

**ASGI Configuration:** `config/asgi.py`
- ASGI application entry point
- WebSocket support (if needed)

**Celery Configuration:** `config/celery_app.py`
- Celery application initialization
- Task autodiscovery
- Beat schedule registration

**URL Configuration:** `config/urls.py`
- Root URL routing
- API endpoint registration
- Admin interface mounting
- Static/media file serving

---

### 10. Monitoring and Observability

#### Health Checks

**Endpoint:** `/healthz`

**Implementation:** `platform_org.health.views`

**Checks:**
- Application responsiveness
- Database connectivity (optional)
- Redis connectivity (optional)

**Usage:**
- Kubernetes liveness probe
- Kubernetes readiness probe
- Load balancer health checks
- Monitoring system integration

#### Logging

**Django Logging:**
- Console output (stdout/stderr)
- Structured logging (JSON format recommended for production)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Celery Logging:**
- Task execution logs
- Worker process logs
- Beat scheduler logs

**Audit Logging:**
- All critical operations logged to `AuditEvent` model
- Immutable audit trail
- Queryable via Django ORM or admin interface

#### Metrics (Recommended)

**Application Metrics:**
- Request count and latency
- Error rates
- Active user sessions
- API endpoint usage

**Business Metrics:**
- SLA breach count and rate
- Autonomy score distribution
- Contract and service counts
- VAM tranche release rate

**Infrastructure Metrics:**
- CPU and memory usage
- Database connection pool
- Redis memory usage
- Celery queue length

**Tools (Not Implemented):**
- Prometheus for metrics collection
- Grafana for visualization
- Sentry for error tracking
- ELK stack for log aggregation

---

## Data Flow Diagrams

### 1. Authentication Flow

```
User → Frontend → API (/api/token/)
                    ↓
              Entra ID Authentication
                    ↓
         Validate JWT signature (JWKS)
                    ↓
         Validate issuer & audience
                    ↓
         Extract user claims (email/upn)
                    ↓
         Get or create Django User
                    ↓
         Attach claims to request
                    ↓
         TenantMiddleware resolves tenant
                    ↓
         Return user + tenant context
```

### 2. Tenant Resolution Flow

```
Request → TenantMiddleware
            ↓
    Check request.entra_claims
            ↓
    Extract tid (tenant ID)
            ↓
    Query Tenant by entra_tenant_id
            ↓
    If not found, check groups
            ↓
    Query Tenant by entra_group_id
            ↓
    If not found and DEBUG=True
            ↓
    Check X-Tenant header
            ↓
    Query Tenant by code
            ↓
    If code="default", auto-create
            ↓
    Set request.tenant
```

### 3. SLA Monitoring Flow

```
Celery Beat (every 5 min)
    ↓
check_sla_breaches task
    ↓
Query OPEN/IN_PROGRESS ServiceRequests
    ↓
For each request:
    ↓
Get contract.sla_template
    ↓
Calculate elapsed hours
    ↓
Check response_time_hours
    ↓
If breached and no first_response_at:
    ↓
Create SLABreachEvent (RESPONSE)
    ↓
Send Teams webhook notification
    ↓
Check resolution_time_hours
    ↓
If breached and no resolved_at:
    ↓
Create SLABreachEvent (RESOLUTION)
    ↓
Send Teams webhook notification
```

### 4. VAM Autonomy Scoring Flow

```
Celery Beat (daily)
    ↓
compute_autonomy_scores task
    ↓
For each MicroEnterprise:
    ↓
Count SLA breaches (provider_me)
    ↓
Count KPI hits (actual >= target)
    ↓
Calculate score:
  100 - (breaches × 10) + (kpi_hit × 5)
    ↓
Assign autonomy level:
  >= 80: HIGH
  >= 50: STANDARD
  < 50: RESTRICTED
    ↓
Update MicroEnterprise.autonomy_level
    ↓
For each VAMAgreement (ACTIVE):
    ↓
For each VAMTranche (PENDING):
    ↓
If score >= 70:
    ↓
Release tranche (status=RELEASED)
    ↓
Record release date
```

### 5. API Request Flow

```
Client → API Endpoint
    ↓
SecurityMiddleware (headers)
    ↓
CorsMiddleware (CORS check)
    ↓
TenantMiddleware (resolve tenant)
    ↓
AuthenticationMiddleware
    ↓
EntraIDAuthentication or JWTAuthentication
    ↓
View (DRF APIView/ViewSet)
    ↓
Permission checks (IsAuthenticated, custom)
    ↓
Queryset filtering (tenant isolation)
    ↓
Serializer validation
    ↓
Business logic execution
    ↓
Database operations (PostgreSQL)
    ↓
Audit logging (if applicable)
    ↓
Response serialization
    ↓
JSON response to client
```

---

## Security Considerations

### 1. Multi-Tenancy Isolation

**Enforcement Layers:**
- **Middleware:** `TenantMiddleware` sets `request.tenant`
- **ORM:** All queries filtered by tenant
- **Serializers:** Validate tenant ownership on create/update
- **Admin:** Custom admin classes respect tenant boundaries

**Risks Mitigated:**
- Cross-tenant data leakage
- Unauthorized access to other tenants' data
- Privilege escalation across tenant boundaries

### 2. Authentication Security

**Entra ID Integration:**
- JWT signature verification prevents token forgery
- Issuer validation prevents token substitution
- Audience validation prevents token misuse
- JWKS rotation support for key management

**Token Management:**
- Short-lived access tokens (60 min default)
- Refresh tokens for session continuity
- Secure token storage (httpOnly cookies recommended)

**Risks Mitigated:**
- Token forgery and tampering
- Replay attacks (via expiration)
- Man-in-the-middle attacks (HTTPS required)

### 3. Authorization Security

**RBAC Implementation:**
- Role-based permissions (PLATFORM_ADMIN, TENANT_ADMIN, MEMBER)
- Row-level permissions via custom permission classes
- Action-based permissions (view, create, update, delete)

**Risks Mitigated:**
- Unauthorized data access
- Privilege escalation
- Horizontal privilege escalation (cross-tenant)

### 4. Data Security

**At Rest:**
- Database encryption (PostgreSQL TDE recommended)
- Secrets management (Kubernetes Secrets, Azure Key Vault)
- Sensitive field encryption (if needed)

**In Transit:**
- HTTPS/TLS for all API communication
- TLS for database connections (ssl_require option)
- Secure WebSocket connections (WSS)

**Risks Mitigated:**
- Data interception
- Credential theft
- Man-in-the-middle attacks

### 5. Input Validation

**Django/DRF Protection:**
- SQL injection prevention (ORM parameterization)
- XSS prevention (template auto-escaping)
- CSRF protection (CSRF middleware)
- JSON schema validation (DRF serializers)

**Risks Mitigated:**
- SQL injection
- Cross-site scripting (XSS)
- Cross-site request forgery (CSRF)
- Mass assignment vulnerabilities

### 6. Audit and Compliance

**Audit Trail:**
- Immutable `AuditEvent` records
- Actor tracking (who did what)
- Timestamp tracking (when)
- Payload tracking (what changed)

**Compliance Support:**
- GDPR: Data access and deletion tracking
- SOC 2: Audit trail for security controls
- ISO 27001: Access control logging

---

## Scalability Considerations

### 1. Horizontal Scaling

**Stateless API:**
- No server-side session state (JWT tokens)
- Shared database and cache (PostgreSQL, Redis)
- Load balancer distribution (Kubernetes Service)

**Scaling Strategy:**
- HPA based on CPU/memory metrics
- Min replicas: 2 (high availability)
- Max replicas: 10+ (configurable)

### 2. Database Scaling

**Read Replicas:**
- PostgreSQL streaming replication
- Read-only queries to replicas
- Write queries to primary

**Connection Pooling:**
- Django connection pooling (conn_max_age=600)
- PgBouncer for external pooling (recommended)

**Partitioning:**
- Tenant-based partitioning (future consideration)
- Time-based partitioning for audit logs

### 3. Caching Strategy

**Redis Caching:**
- Query result caching
- Session caching
- API response caching (per-view)

**Cache Invalidation:**
- Time-based expiration
- Event-based invalidation (signals)
- Cache key versioning

### 4. Background Task Scaling

**Celery Workers:**
- Multiple worker instances
- Task routing by queue
- Priority queues for critical tasks

**Celery Beat:**
- Single instance (leader election)
- Distributed locking for task execution

### 5. Performance Optimization

**Database Indexes:**
- Tenant ID on all tables
- Foreign key indexes
- Composite indexes for common queries
- Created_at indexes for time-based queries

**Query Optimization:**
- select_related() for foreign keys
- prefetch_related() for many-to-many
- Queryset filtering at database level
- Pagination for large result sets

**Static Assets:**
- WhiteNoise for static file serving
- Compressed and cached static files
- CDN integration (recommended)

---

## Technology Stack Summary

### Backend
- **Framework:** Django 5.x
- **API:** Django REST Framework 3.15+
- **ASGI Server:** Gunicorn + Uvicorn workers
- **Task Queue:** Celery 5.4+
- **Scheduler:** Celery Beat
- **Authentication:** PyJWT 2.9+ (Entra ID), djangorestframework-simplejwt 5.3+

### Frontend
- **Framework:** React (Vite)
- **UI Library:** Microsoft Fluent UI
- **Build Tool:** Vite
- **Routing:** React Router (implied)

### Data Stores
- **Database:** PostgreSQL 16
- **Cache/Broker:** Redis 7
- **ORM:** Django ORM

### Infrastructure
- **Containerization:** Docker
- **Orchestration:** Kubernetes
- **Ingress:** Traefik
- **Package Management:** Helm
- **Python Package Manager:** uv

### Development Tools
- **API Documentation:** drf-spectacular (OpenAPI 3.0)
- **Static Files:** WhiteNoise 6.x
- **CORS:** django-cors-headers 4.4+
- **Environment:** django-environ 0.11+

### External Integrations
- **Identity Provider:** Azure Entra ID (Azure AD)
- **Notifications:** Microsoft Teams (webhooks)
- **Ticketing:** Jitbit, Jira

---

## Deployment Checklist

### Pre-Deployment
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Generate strong `DJANGO_SECRET_KEY`
- [ ] Configure `DJANGO_ALLOWED_HOSTS`
- [ ] Set up PostgreSQL database
- [ ] Set up Redis instance
- [ ] Configure Entra ID application
- [ ] Set `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_ALLOWED_ISSUER`
- [ ] Configure `TEAMS_WEBHOOK_URL` for alerts
- [ ] Set `CORS_ALLOWED_ORIGINS` for frontend
- [ ] Review and update Helm `values.yaml`

### Database Setup
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Seed initial data: `python manage.py seed_platform_org`
- [ ] Verify tenant configuration
- [ ] Set up database backups

### Kubernetes Deployment
- [ ] Create namespace: `kubectl apply -f deploy/k8s/namespace.yaml`
- [ ] Create secrets (database, Redis, Entra ID)
- [ ] Deploy via Helm: `helm install platform-org ./deploy/helm/platform-org`
- [ ] Verify pod status: `kubectl get pods -n platform-org`
- [ ] Check logs: `kubectl logs -n platform-org <pod-name>`
- [ ] Verify health endpoint: `curl https://api.example.com/healthz`

### Post-Deployment
- [ ] Test authentication flow (Entra ID)
- [ ] Verify tenant isolation
- [ ] Test SLA monitoring (create test service request)
- [ ] Verify Celery tasks execution
- [ ] Test Teams webhook notifications
- [ ] Review audit logs
- [ ] Set up monitoring and alerting
- [ ] Configure backup and disaster recovery

---

## Maintenance and Operations

### Regular Tasks

**Daily:**
- Monitor Celery task execution
- Review SLA breach alerts
- Check application logs for errors

**Weekly:**
- Review audit logs
- Analyze autonomy score trends
- Check database performance metrics

**Monthly:**
- Database maintenance (VACUUM, ANALYZE)
- Review and rotate secrets
- Update dependencies (security patches)

### Backup Strategy

**Database Backups:**
- Daily full backups
- Continuous WAL archiving (PostgreSQL)
- Retention: 30 days minimum
- Test restore procedures quarterly

**Configuration Backups:**
- Version control for all configuration files
- Helm values stored securely
- Kubernetes manifests in Git

### Monitoring Alerts

**Critical Alerts:**
- API service down
- Database connection failures
- Celery worker failures
- High error rate (>5%)

**Warning Alerts:**
- High response time (>2s p95)
- High CPU/memory usage (>80%)
- Celery queue backlog (>100 tasks)
- SLA breach rate increase

### Disaster Recovery

**RTO (Recovery Time Objective):** 4 hours
**RPO (Recovery Point Objective):** 1 hour

**Recovery Procedures:**
1. Restore database from latest backup
2. Deploy application from last known good version
3. Verify data integrity
4. Resume Celery workers
5. Validate critical workflows

---

## Future Enhancements

### Planned Features
- Real-time notifications via WebSockets
- Advanced analytics dashboard
- Machine learning for autonomy prediction
- Multi-region deployment support
- GraphQL API endpoint
- Mobile application (React Native)

### Technical Debt
- Implement comprehensive test suite (unit, integration, e2e)
- Add Prometheus metrics export
- Implement distributed tracing (OpenTelemetry)
- Add rate limiting and throttling
- Implement API versioning
- Add database query performance monitoring

### Scalability Improvements
- Implement read replicas for PostgreSQL
- Add CDN for static assets
- Implement API response caching
- Add database connection pooling (PgBouncer)
- Implement task result expiration in Redis
- Add Celery task prioritization

---

## Appendix

### Key Files Reference

**Configuration:**
- `config/settings.py` - Django settings
- `config/urls.py` - URL routing
- `config/asgi.py` - ASGI application
- `config/celery_app.py` - Celery configuration

**Models:**
- `platform_org/core/models.py` - Core business models
- `platform_org/sla/models.py` - SLA monitoring models
- `platform_org/tenancy/models.py` - Multi-tenancy models
- `platform_org/audit/models.py` - Audit logging models

**Authentication:**
- `platform_org/core/authentication.py` - Entra ID authentication
- `platform_org/tenancy/middleware.py` - Tenant resolution

**Background Tasks:**
- `platform_org/sla/tasks.py` - SLA monitoring tasks
- `platform_org/core/vam_engine.py` - VAM autonomy scoring
- `platform_org/integrations/tasks.py` - Integration tasks

**Deployment:**
- `docker-compose.yml` - Local development stack
- `docker/Dockerfile` - Container image definition
- `deploy/k8s/` - Kubernetes manifests
- `deploy/helm/platform-org/` - Helm chart

**Dependencies:**
- `pyproject.toml` - Python dependencies
- `uv.lock` - Locked dependency versions

### Glossary

- **ME (Micro Enterprise):** Self-organizing business unit in Rendanheyi model
- **VAM (Value-Added Management):** Performance-based funding mechanism
- **SLA (Service Level Agreement):** Contractual service quality commitments
- **Entra ID:** Microsoft's identity and access management service (formerly Azure AD)
- **JWKS (JSON Web Key Set):** Public keys for JWT signature verification
- **HPA (Horizontal Pod Autoscaler):** Kubernetes auto-scaling mechanism
- **RBAC (Role-Based Access Control):** Permission model based on user roles
- **ASGI (Asynchronous Server Gateway Interface):** Python async web server standard

### Contact and Support

**Project Repository:** (Add Git repository URL)
**Documentation:** (Add documentation site URL)
**Issue Tracker:** (Add issue tracker URL)
**Team Contact:** (Add team email or Slack channel)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-09
**Maintained By:** Platform Org Development Team
