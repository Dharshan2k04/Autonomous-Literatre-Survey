# Autonomous Literature Survey System

A production-grade **Agentic RAG** (Retrieval-Augmented Generation) application that automates academic literature review through a four-stage AI agent workflow. Built with FastAPI, React, LangGraph, and deployable on AWS ECS Fargate.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  Login/Register ─── Survey Dashboard ─── Detail View ─── Chat  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST + WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  Auth ── Survey CRUD ── RAG Chat ── WebSocket Progress          │
├─────────────────────────────────────────────────────────────────┤
│                   LangGraph Agent Workflow                       │
│                                                                 │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────────┐ │
│  │    Query      │  │    Citation     │  │      IEEE          │ │
│  │  Strategist   │→│    Explorer     │→│    Formatter       │ │
│  │  (Agent 1)    │  │  (Agent 2)     │  │   (Agent 3)        │ │
│  └──────────────┘  └─────────────────┘  └────────────────────┘ │
│                                                │                │
│                                    ┌───────────▼──────────────┐ │
│                                    │     Survey Architect     │ │
│                                    │       (Agent 4)          │ │
│                                    └──────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  External APIs: Semantic Scholar │ arXiv │ Crossref             │
│  LLM: OpenAI (GPT-4o) │ Anthropic (Claude) │ Mock fallback     │
│  Vector DB: Pinecone │ Cache: Redis │ DB: PostgreSQL            │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Workflow

| Stage | Agent | Function |
|-------|-------|----------|
| 1 | **Query Strategist** | Expands research topic into optimized sub-queries using LLM |
| 2 | **Citation Explorer** | Searches Semantic Scholar, arXiv, Crossref in parallel; deduplicates and ranks papers |
| 3 | **IEEE Formatter** | Generates IEEE-standard citations for all discovered papers |
| 4 | **Survey Architect** | Clusters papers, builds taxonomy, generates full markdown survey |

## Tech Stack

### Backend
- **Python 3.11** + **FastAPI** (async)
- **SQLAlchemy 2.0** (async) + **Alembic** migrations
- **LangGraph** for agent orchestration
- **OpenAI** / **Anthropic** (pluggable LLM)
- **Pinecone** vector database
- **Redis** for caching & real-time progress

### Frontend
- **React 18** + **TypeScript** + **Vite**
- **TailwindCSS** with dark theme
- **Zustand** state management
- **TanStack Query** for data fetching
- **WebSocket** real-time updates

### Infrastructure
- **Docker** multi-stage builds
- **AWS ECS Fargate** (auto-scaling 2–4 tasks)
- **RDS PostgreSQL** + **ElastiCache Redis**
- **ALB** with path-based routing
- **Terraform** IaC
- **GitHub Actions** CI/CD

---

## Running the Project — Step-by-Step

### Prerequisites

Make sure the following tools are installed and available on your `PATH`:

| Tool | Required version | Check |
|------|-----------------|-------|
| Git | any | `git --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | v2 (bundled with Docker Desktop) | `docker compose version` |
| Node.js | 20+ (local dev only) | `node --version` |
| Python | 3.11+ (local dev only) | `python --version` |

> **Tip:** Docker Desktop for Mac/Windows bundles Docker Engine and Docker Compose v2. Linux users should install the `docker-compose-plugin` package.

---

### Option A — Docker Compose (Recommended)

This is the fastest path. Docker Compose starts PostgreSQL, Redis, the FastAPI backend, and the React frontend together.

#### Step 1 — Clone the repository

```bash
git clone https://github.com/Dharshan2k04/Autonomous-Literatre-Survey.git
cd Autonomous-Literatre-Survey
```

#### Step 2 — Create your environment file

```bash
cp .env.example .env
```

Open `.env` in a text editor and fill in the values you need. The minimum required fields for a working local setup are:

```ini
# Mandatory — change to any long random string (used for JWT signing)
SECRET_KEY=replace-with-a-long-random-string-at-least-32-chars

# Optional — add an OpenAI or Anthropic key for real LLM responses
# Without an LLM key the agents return mock/fallback responses
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# Optional — add a Pinecone key for semantic search; otherwise skipped
PINECONE_API_KEY=...
```

> **Note:** `DATABASE_URL`, `REDIS_HOST`, and `REDIS_PORT` are automatically overridden by `docker-compose.yml` when running with Docker Compose, so you do not need to change those values.

Generate a secure `SECRET_KEY` with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### Step 3 — Build and start all services

```bash
docker compose up --build
```

Docker Compose will:
1. Pull `postgres:16-alpine` and `redis:7-alpine` images
2. Build the backend image from `backend/Dockerfile`
3. Build the frontend image from `frontend/Dockerfile`
4. Start all four containers and wait for the database health check to pass before starting the backend

The first build takes 3–5 minutes. Subsequent starts (without `--build`) are much faster.

#### Step 4 — Run database migrations

In a **second terminal**, with the containers running:

```bash
docker compose exec backend alembic upgrade head
```

This creates the `users`, `surveys`, and `papers` tables in PostgreSQL. You should see output ending with:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, Initial schema — users, surveys, papers
```

#### Step 5 — Open the application

| Service | URL |
|---------|-----|
| Frontend (React) | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Interactive API Docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |

#### Step 6 — Register an account and create a survey

1. Go to http://localhost:3000
2. Click **Sign Up** and register with any email/password
3. Click **New Survey**, enter a research topic (e.g. *"Transformer architectures for NLP"*), and click **Start Survey**
4. The four-stage agent pipeline runs in the background. A progress bar shows each stage. WebSocket updates are pushed in real time.
5. When the status changes to **Completed**, switch to the **Survey** tab to read the generated markdown document.

#### Stopping the stack

```bash
docker compose down          # stop containers, keep data volumes
docker compose down -v       # stop containers AND delete all data (fresh start)
```

---

### Option B — Local Development (without Docker)

Use this approach when you want hot-reload on both backend and frontend simultaneously.

You still need PostgreSQL and Redis running locally. The quickest way is to start just those two services via Docker:

```bash
docker compose up postgres redis -d
```

Or install them natively on your OS.

#### Backend

```bash
# 1. Enter the backend directory
cd backend

# 2. Create a Python virtual environment
python -m venv .venv

# 3. Activate the virtual environment
#    macOS / Linux:
source .venv/bin/activate
#    Windows (Command Prompt):
.venv\Scripts\activate.bat
#    Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy and edit the environment file (if not already done at repo root)
#    The backend reads .env from the CURRENT directory when starting,
#    so create a symlink or copy:
cp ../.env .env         # or: ln -s ../.env .env

# 6. Run database migrations
alembic upgrade head

# 7. Start the development server with auto-reload
uvicorn app.main:app --reload --port 8000
```

The backend is available at http://localhost:8000. Swagger UI is at http://localhost:8000/docs (because `DEBUG=true` in the default config).

> **Tip:** `--reload` watches for file changes and restarts automatically. Remove it for a production-like start.

#### Frontend

Open a **new terminal**:

```bash
# 1. Enter the frontend directory
cd frontend

# 2. Install Node.js dependencies
npm install

# 3. Start the Vite dev server
npm run dev
```

The frontend is available at http://localhost:5173 with hot module replacement. `vite.config.ts` automatically proxies `/api` and `/ws` requests to `http://localhost:8000`, so no extra configuration is needed.

---

### Running the Test Suite

#### Backend tests

```bash
cd backend

# Install dev dependencies (if not already installed)
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite

# Run all tests
pytest tests/ -v

# Run only tests that don't need a database (security, config)
pytest tests/test_security.py tests/test_health.py -v

# Run with coverage report
pytest tests/ -v --cov=app --cov-report=term-missing
```

> **Note:** Integration tests (`test_surveys.py`, `test_auth.py`) require a running PostgreSQL database. Set `DATABASE_URL` in your environment or use the Docker-based PostgreSQL:
> ```bash
> docker compose up postgres -d
> ```

#### Frontend lint & build check

```bash
cd frontend
npm install
npm run lint      # ESLint
npm run build     # TypeScript type-check + Vite production build
```

---

### Linting the Backend

```bash
cd backend
pip install ruff
ruff check app/          # lint
ruff check --fix app/    # lint and auto-fix safe issues
```

---

## Environment Variables Reference

All variables are read from `.env` (or from the process environment). Docker Compose injects `DATABASE_URL`, `REDIS_HOST`, and `REDIS_PORT` directly, so those do not need to be set in `.env` for the Docker workflow.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | `change-me-…` | Secret used for JWT signing and session cookies. Must be changed before any real use. |
| `ENVIRONMENT` | No | `development` | `development` enables Swagger UI (`/docs`) and debug logging. Set to `production` to disable. |
| `DEBUG` | No | `false` | Enables SQLAlchemy query logging and Swagger UI. |
| `POSTGRES_HOST` | No | `localhost` | PostgreSQL host. Overridden to `postgres` by Docker Compose. |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port. |
| `POSTGRES_USER` | No | `als_user` | PostgreSQL username. |
| `POSTGRES_PASSWORD` | No | `als_password` | PostgreSQL password. |
| `POSTGRES_DB` | No | `als_db` | PostgreSQL database name. |
| `REDIS_HOST` | No | `localhost` | Redis hostname. Overridden to `redis` by Docker Compose. |
| `REDIS_PORT` | No | `6379` | Redis port. |
| `REDIS_PASSWORD` | No | *(empty)* | Redis password (if auth is enabled). |
| `OPENAI_API_KEY` | No* | *(empty)* | OpenAI API key for GPT-4o LLM and text-embedding-3-large. |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI chat model to use. |
| `ANTHROPIC_API_KEY` | No* | *(empty)* | Anthropic API key for Claude. |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-20250514` | Anthropic model to use. |
| `LLM_PROVIDER` | No | `openai` | Active LLM provider: `openai` or `anthropic`. |
| `PINECONE_API_KEY` | No | *(empty)* | Pinecone API key. If absent, semantic search / RAG is skipped. |
| `PINECONE_INDEX_NAME` | No | `literature-survey` | Pinecone index name. |
| `SEMANTIC_SCHOLAR_API_KEY` | No | *(empty)* | Semantic Scholar key for higher rate limits. Works unauthenticated at lower limits. |
| `CROSSREF_EMAIL` | No | *(empty)* | Polite Pool email for Crossref API (higher rate limits). |
| `GOOGLE_CLIENT_ID` | No | *(empty)* | Google OAuth 2.0 client ID. |
| `GOOGLE_CLIENT_SECRET` | No | *(empty)* | Google OAuth 2.0 client secret. |
| `GITHUB_CLIENT_ID` | No | *(empty)* | GitHub OAuth app client ID. |
| `GITHUB_CLIENT_SECRET` | No | *(empty)* | GitHub OAuth app client secret. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token lifetime in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | JWT refresh token lifetime in days. |
| `BACKEND_CORS_ORIGINS` | No | `["http://localhost:5173","http://localhost:3000"]` | Allowed CORS origins as a JSON array. |

*At least one LLM key (`OPENAI_API_KEY` **or** `ANTHROPIC_API_KEY`) is strongly recommended. Without one, every agent stage falls back to deterministic mock responses, which means the generated survey will not contain real paper data or meaningful content.

---

## Troubleshooting

### `docker compose up` fails with "connection refused" on the backend

The backend waits for the PostgreSQL health check. If it still fails, inspect the database logs:

```bash
docker compose logs postgres
```

Common causes: the port 5432 is already in use on your machine (local PostgreSQL instance), or Docker does not have enough memory. Try `docker compose down -v` then `docker compose up --build`.

### `alembic upgrade head` reports "can't connect to database"

When running locally (Option B), make sure PostgreSQL is up and that the `POSTGRES_*` variables in `.env` match the running database:

```bash
# Quickly test connectivity:
psql postgresql://als_user:als_password@localhost:5432/als_db -c "SELECT 1"
```

If using the Docker-based PostgreSQL (credentials from `docker-compose.yml`):

```bash
# Use these credentials instead:
psql postgresql://litsurvey:litsurvey_dev@localhost:5432/litsurvey -c "SELECT 1"
```

And update your local `.env` accordingly:

```ini
POSTGRES_USER=litsurvey
POSTGRES_PASSWORD=litsurvey_dev
POSTGRES_DB=litsurvey
```

### Survey stays in "pending" or "query_expansion" forever

This is normal when no LLM key is set — the agent falls back to mock data immediately. If you have an API key set but the survey is stuck, check the backend logs:

```bash
docker compose logs backend -f
# or, for local dev:
# tail -f the uvicorn console output
```

Look for `workflow_failed` log entries for the specific error.

### Frontend shows "Failed to load surveys" or 401 errors

1. Make sure the backend is running and healthy: `curl http://localhost:8000/api/v1/health`
2. Clear `localStorage` in the browser (the JWT may be expired), then log in again.
3. Verify `BACKEND_CORS_ORIGINS` in `.env` includes the frontend URL you are using (`http://localhost:3000` for Docker, `http://localhost:5173` for Vite dev server).

### Port conflicts

| Service | Default port | Change |
|---------|-------------|--------|
| Frontend | 3000 | Edit `docker-compose.yml` `frontend.ports` |
| Backend | 8000 | Edit `docker-compose.yml` `backend.ports` |
| PostgreSQL | 5432 | Edit `docker-compose.yml` `postgres.ports` |
| Redis | 6379 | Edit `docker-compose.yml` `redis.ports` |
| Vite dev server | 5173 | Edit `frontend/vite.config.ts` `server.port` |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Liveness probe |
| `GET` | `/api/v1/health/ready` | Readiness probe (checks LLM / Pinecone config) |
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login with credentials |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT access token |
| `GET` | `/api/v1/auth/me` | Get current user profile |
| `GET` | `/api/v1/auth/google/login` | Redirect to Google OAuth |
| `GET` | `/api/v1/auth/github/login` | Redirect to GitHub OAuth |
| `POST` | `/api/v1/surveys` | Create & start a new survey |
| `GET` | `/api/v1/surveys` | List user's surveys (paginated) |
| `GET` | `/api/v1/surveys/{id}` | Get survey detail + markdown |
| `DELETE` | `/api/v1/surveys/{id}` | Delete survey and all papers |
| `GET` | `/api/v1/surveys/{id}/papers` | List all papers for a survey |
| `POST` | `/api/v1/surveys/{id}/chat` | RAG chat over the survey's papers |
| `WS` | `/ws/surveys/{survey_id}` | Real-time pipeline progress |

---

## AWS Deployment

### Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform >= 1.5
- An S3 bucket for Terraform remote state

### Steps

```bash
cd infrastructure/terraform

# 1. Initialise providers and remote state
terraform init

# 2. Preview the changes
terraform plan \
  -var="db_password=YOUR_SECURE_PASSWORD" \
  -var="secret_key=YOUR_SECRET_KEY" \
  -var="backend_image=YOUR_ECR_URI/litsurvey-backend:latest" \
  -var="frontend_image=YOUR_ECR_URI/litsurvey-frontend:latest"

# 3. Apply
terraform apply
```

### CI/CD

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) runs automatically on every push to `main`:

1. **Lint** — Ruff (Python) + TypeScript check
2. **Test** — Backend `pytest` + frontend `npm run build`
3. **Build** — Docker images pushed to ECR
4. **Deploy** — ECS services force new deployment

Required GitHub Secrets:
- `AWS_ROLE_ARN` — IAM role ARN for OIDC-based authentication

---

## Testing

```bash
# Backend — all tests (requires PostgreSQL)
cd backend
pytest tests/ -v --cov=app

# Backend — security & config tests only (no database needed)
pytest tests/test_security.py tests/test_health.py -v

# Frontend — lint and build check
cd frontend
npm run lint
npm run build
```

---

## Project Structure

```
├── .github/workflows/ci-cd.yml    # CI/CD pipeline
├── .env.example                    # Environment template
├── docker-compose.yml              # Local development stack
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                    # Database migrations
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   └── app/
│       ├── config.py               # Settings (pydantic-settings)
│       ├── database.py             # Async DB engine & session
│       ├── main.py                 # FastAPI app factory
│       ├── models/                 # SQLAlchemy ORM models
│       ├── schemas/                # Pydantic request/response schemas
│       ├── core/                   # Security, logging, exceptions
│       ├── services/               # Business logic layer
│       ├── external/               # Semantic Scholar / arXiv / Crossref clients
│       ├── agents/                 # LangGraph agent implementations
│       ├── api/v1/                 # REST route handlers
│       └── websocket/              # WebSocket progress handler
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── components/             # Shared UI components
│       ├── pages/                  # Route-level page components
│       ├── hooks/                  # Custom React hooks (WebSocket, etc.)
│       ├── store/                  # Zustand global state
│       ├── services/               # Axios API client & endpoints
│       └── types/                  # TypeScript type definitions
│
└── infrastructure/terraform/
    ├── main.tf                     # Provider & backend config
    ├── modules.tf                  # Module orchestration
    ├── variables.tf                # Input variables
    ├── outputs.tf                  # Output values
    └── modules/
        ├── networking/             # VPC, subnets, security groups
        ├── ecr/                    # Container registries
        ├── rds/                    # RDS PostgreSQL
        ├── elasticache/            # ElastiCache Redis
        ├── alb/                    # Application Load Balancer
        └── ecs/                    # ECS Fargate services
```

---

## Key Design Decisions

- **Graceful Degradation**: System works without LLM keys (mock responses), without Pinecone (skip embeddings), without Redis (no caching, still functional)
- **Pluggable LLM**: Switch between OpenAI and Anthropic via `LLM_PROVIDER` environment variable
- **Parallel Search**: Citation Explorer queries 3 academic APIs concurrently with `asyncio.gather`
- **Custom Clustering**: Numpy-based k-means avoids a heavy scikit-learn dependency
- **Background Processing**: Survey generation runs as a FastAPI `BackgroundTask` with WebSocket real-time progress updates
- **API Versioning**: All endpoints under `/api/v1/` for future compatibility

---

## License

MIT