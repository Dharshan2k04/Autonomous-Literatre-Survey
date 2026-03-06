# Autonomous Literature Survey System

A production-grade **Agentic RAG** (Retrieval-Augmented Generation) application that automates academic literature review through a four-stage AI agent workflow. Built with FastAPI, React, LangGraph, and deployed on AWS ECS Fargate.

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

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Clone & Configure

```bash
git clone https://github.com/Dharshan2k04/Autonomous-Literatre-Survey.git
cd Autonomous-Literatre-Survey
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 3. Run Database Migrations

```bash
docker compose exec backend alembic upgrade head
```

### Local Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_HOST` | Yes | PostgreSQL host (default: `localhost`) |
| `POSTGRES_PORT` | Yes | PostgreSQL port (default: `5432`) |
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DB` | Yes | PostgreSQL database name |
| `DATABASE_URL` | No | Full PostgreSQL URL — overrides `POSTGRES_*` fields when set |
| `SECRET_KEY` | Yes | Secret for JWT tokens and session signing |
| `REDIS_HOST` | No | Redis host (graceful degradation) |
| `OPENAI_API_KEY` | No* | OpenAI API key |
| `ANTHROPIC_API_KEY` | No* | Anthropic API key |
| `PINECONE_API_KEY` | No | Pinecone vector DB key |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Higher rate limits |
| `GOOGLE_CLIENT_ID` | No | Google OAuth |
| `GITHUB_CLIENT_ID` | No | GitHub OAuth |

*At least one LLM key recommended. System falls back to mock responses without keys.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login with credentials |
| `GET` | `/api/v1/auth/me` | Get current user |
| `POST` | `/api/v1/surveys` | Create & start survey |
| `GET` | `/api/v1/surveys` | List user's surveys |
| `GET` | `/api/v1/surveys/{id}` | Get survey detail |
| `DELETE` | `/api/v1/surveys/{id}` | Delete survey |
| `GET` | `/api/v1/surveys/{id}/papers` | List survey papers |
| `POST` | `/api/v1/chat/{survey_id}` | RAG chat about survey |
| `WS` | `/ws/survey/{survey_id}` | Real-time progress |

---

## AWS Deployment

### Prerequisites
- AWS CLI configured
- Terraform >= 1.5
- S3 bucket for Terraform state

### Deploy

```bash
cd infrastructure/terraform

# Initialize
terraform init

# Plan
terraform plan \
  -var="db_password=YOUR_SECURE_PASSWORD" \
  -var="jwt_secret_key=YOUR_JWT_SECRET" \
  -var="backend_image=YOUR_ECR_URI/litsurvey-backend:latest" \
  -var="frontend_image=YOUR_ECR_URI/litsurvey-frontend:latest"

# Apply
terraform apply
```

### CI/CD

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) runs:

1. **Lint** — Ruff + TypeScript check
2. **Test** — Backend pytest + frontend build
3. **Build** — Docker images pushed to ECR
4. **Deploy** — ECS services force new deployment

Required GitHub Secrets:
- `AWS_ROLE_ARN` — IAM role for OIDC

---

## Testing

```bash
# Backend — no database required (uses SQLite in-memory)
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite

# All tests
pytest tests/ -v --cov=app

# Security unit tests only (no infrastructure needed at all)
pytest tests/test_security.py -v
```

---

## Project Structure

```
├── .github/workflows/ci-cd.yml    # CI/CD pipeline
├── .env.example                    # Environment template
├── docker-compose.yml              # Local development
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                    # Database migrations
│   └── app/
│       ├── config.py               # Settings
│       ├── database.py             # Async DB engine
│       ├── main.py                 # FastAPI app
│       ├── models/                 # SQLAlchemy models
│       ├── schemas/                # Pydantic schemas
│       ├── core/                   # Security, logging, exceptions
│       ├── services/               # Business logic
│       ├── external/               # API clients
│       ├── agents/                 # LangGraph agents
│       ├── api/v1/                 # REST endpoints
│       └── websocket/              # WebSocket handlers
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── components/             # React components
│       ├── pages/                  # Page components
│       ├── hooks/                  # Custom hooks
│       ├── store/                  # Zustand stores
│       ├── services/               # API layer
│       └── types/                  # TypeScript types
│
└── infrastructure/terraform/
    ├── main.tf                     # Provider config
    ├── modules.tf                  # Module orchestration
    ├── variables.tf                # Input variables
    ├── outputs.tf                  # Outputs
    └── modules/
        ├── networking/             # VPC, subnets, SGs
        ├── ecr/                    # Container registries
        ├── rds/                    # PostgreSQL
        ├── elasticache/            # Redis
        ├── alb/                    # Load balancer
        └── ecs/                    # Fargate services
```

---

## Key Design Decisions

- **Graceful Degradation**: System works without LLM keys (mock responses), without Pinecone (skip embeddings), without Redis (no caching, still functional)
- **Pluggable LLM**: Switch between OpenAI and Anthropic via environment variable
- **Parallel Search**: Citation Explorer queries 3 academic APIs concurrently
- **Custom Clustering**: Numpy-based k-means avoids heavy sklearn dependency
- **Background Processing**: Survey generation runs as FastAPI background task with WebSocket progress updates
- **API Versioning**: All endpoints under `/api/v1/` for future compatibility

---

## License

MIT