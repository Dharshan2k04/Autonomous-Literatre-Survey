# 📚 Autonomous Literature Survey System

A **production-grade Agentic RAG application** that automates academic literature review through a four-stage AI agent workflow. Built with FastAPI, LangGraph, GPT-4, Pinecone, and deployed on AWS ECS Fargate.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Query Strategist Agent** | GPT-4 expands a research topic into 3 targeted sub-queries via LangGraph |
| **Citation Explorer Agent** | Parallel API calls to Semantic Scholar, arXiv & Crossref; dedup by DOI/title similarity; rank by citations & recency |
| **IEEE Formatter Agent** | Generates publication-ready IEEE citations + 2-3 sentence contextual summaries |
| **Survey Architect Agent** | Clusters papers with embedding similarity; identifies research gaps; compiles structured markdown survey |
| **RAG Chat Interface** | Real-time WebSocket chat backed by Pinecone vector search and GPT-4 |
| **REST API** | FastAPI + SQLAlchemy + PostgreSQL for persistent storage |
| **AWS Infrastructure** | ECS Fargate, RDS PostgreSQL, ElastiCache Redis, ALB, CloudWatch – all managed by Terraform |

---

## 🏗 Architecture

```
┌──────────────┐     REST / WS     ┌───────────────────────────────────────┐
│ React        │ ◄────────────────► │ FastAPI Backend                       │
│ Frontend     │                    │                                       │
│ (Vite + TW)  │                    │  ┌─────────────────────────────────┐  │
└──────────────┘                    │  │ 4-Stage Agent Pipeline          │  │
                                    │  │                                 │  │
                                    │  │ 1. Query Strategist (LangGraph) │  │
                                    │  │ 2. Citation Explorer (3 APIs)   │  │
                                    │  │ 3. IEEE Formatter (GPT-4)       │  │
                                    │  │ 4. Survey Architect (GPT-4)     │  │
                                    │  └─────────────────────────────────┘  │
                                    │                                       │
                                    │  ┌──────────┐  ┌──────────────────┐  │
                                    │  │ Pinecone │  │ PostgreSQL (RDS) │  │
                                    │  │ Vector DB│  │ + Redis Cache    │  │
                                    │  └──────────┘  └──────────────────┘  │
                                    └───────────────────────────────────────┘
```

### AWS Infrastructure

```
Internet → ALB → ECS Fargate (frontend + backend)
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
     RDS PostgreSQL    ElastiCache Redis
      (private subnet)  (private subnet)
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Docker & Docker Compose
- OpenAI API key
- Pinecone API key

### 1. Clone and configure

```bash
git clone https://github.com/Dharshan2k04/Autonomous-Literatre-Survey
cd Autonomous-Literatre-Survey
cp .env.example .env
# Edit .env and fill in your OPENAI_API_KEY and PINECONE_API_KEY
```

### 2. Start all services

```bash
docker compose up --build
```

The app will be available at **http://localhost**.

| Service | URL |
|---|---|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## 🖥 Frontend Development

```bash
cd frontend
npm install
npm run dev       # Vite dev server on http://localhost:5173
```

---

## 🔧 Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL + Redis (via Docker)
docker compose up postgres redis -d

cp ../.env.example ../.env  # and fill in values

uvicorn app.main:app --reload --port 8000
```

---

## 🌩 AWS Deployment

### Prerequisites

- AWS CLI configured (`aws configure`)
- Terraform ≥ 1.6
- Docker (for pushing images to ECR)

### 1. Initialise Terraform

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars   # fill in values
terraform init
terraform plan
terraform apply
```

### 2. Build & push Docker images

```bash
# Backend
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

docker build -t autlit-survey-backend ./backend
docker tag autlit-survey-backend:latest <ECR_BACKEND_URL>:latest
docker push <ECR_BACKEND_URL>:latest

# Frontend
docker build -t autlit-survey-frontend ./frontend
docker tag autlit-survey-frontend:latest <ECR_FRONTEND_URL>:latest
docker push <ECR_FRONTEND_URL>:latest
```

### 3. Deploy services

```bash
aws ecs update-service --cluster autlit-survey-prod-cluster \
  --service autlit-survey-prod-backend --force-new-deployment
aws ecs update-service --cluster autlit-survey-prod-cluster \
  --service autlit-survey-prod-frontend --force-new-deployment
```

After deployment, retrieve the ALB DNS name from Terraform outputs:

```bash
terraform output alb_dns_name
```

---

## 📁 Project Structure

```
Autonomous-Literature-Survey/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry-point
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   ├── models/
│   │   │   └── survey.py        # Survey & Paper ORM models
│   │   ├── agents/
│   │   │   ├── query_strategist.py   # LangGraph + GPT-4 query expansion
│   │   │   ├── citation_explorer.py  # Parallel Semantic Scholar/arXiv/Crossref
│   │   │   ├── ieee_formatter.py     # IEEE citations + summaries
│   │   │   └── survey_architect.py   # Clustering + gaps + survey compilation
│   │   ├── api/
│   │   │   ├── surveys.py       # REST CRUD endpoints
│   │   │   └── websocket.py     # WebSocket RAG chat
│   │   └── services/
│   │       ├── pinecone_service.py  # Embedding + vector upsert/query
│   │       └── redis_service.py     # Caching helpers
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx         # Survey list with status polling
│   │   │   ├── NewSurvey.jsx    # Survey creation form
│   │   │   └── SurveyDetail.jsx # Survey view + papers + chat
│   │   ├── hooks/
│   │   │   └── useSurveyChat.js # WebSocket chat hook
│   │   ├── services/
│   │   │   └── api.js           # Axios API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── nginx.conf
│   ├── vite.config.js
│   └── Dockerfile
├── infrastructure/
│   ├── main.tf                  # Terraform provider + locals
│   ├── variables.tf             # All input variables
│   ├── networking.tf            # VPC, subnets, SGs, NAT
│   ├── alb.tf                   # Application Load Balancer
│   ├── ecs.tf                   # ECS cluster, tasks, services, auto-scaling
│   ├── rds.tf                   # RDS PostgreSQL
│   ├── redis.tf                 # ElastiCache Redis
│   └── outputs.tf               # Terraform outputs
├── docker-compose.yml           # Local dev orchestration
├── .env.example                 # Environment variable template
└── README.md
```

---

## 🔌 API Reference

### REST

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/surveys/` | Create survey (triggers async pipeline) |
| `GET` | `/api/v1/surveys/` | List all surveys |
| `GET` | `/api/v1/surveys/{id}` | Get survey with papers |
| `DELETE` | `/api/v1/surveys/{id}` | Delete survey |
| `GET` | `/health` | Health check |

### WebSocket

```
ws://host/ws/chat/{survey_id}
```

**Send:**
```json
{ "message": "What are the main approaches to protein structure prediction?" }
```

**Receive (typing indicator):**
```json
{ "type": "typing", "content": "" }
```

**Receive (answer):**
```json
{ "type": "message", "role": "assistant", "content": "Based on [1] and [3]..." }
```

---

## 🛡 Security

- API keys stored in AWS SSM Parameter Store (SecureString, encrypted at rest)
- RDS and ElastiCache deployed in private subnets (no public access)
- ECS tasks run as non-root users
- Container image scanning enabled in ECR
- ALB access logs stored in S3 with 30-day lifecycle policy

---

## 📄 License

MIT