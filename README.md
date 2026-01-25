# Call Center Audio Intelligence

A system that processes call center audio recordings to extract transcriptions and generate AI-powered analysis. The application provides performance metrics, sentiment analysis, sales intelligence, and actionable recommendations through a web-based dashboard.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Running with Docker (Recommended)](#running-with-docker-recommended)
- [Running Locally (Development)](#running-locally-development)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Features

**Audio Processing**
- Upload audio files in common formats (MP3, WAV, M4A, FLAC, OGG, WEBM)
- Automatic transcription using Replicate's Whisper model
- Speaker diarization and language detection

**AI Analysis**
- Call sentiment analysis (positive, negative, neutral)
- Employee performance scoring (0-100)
- Customer intent detection
- Buying signals and objection identification
- Conversion likelihood prediction
- Auto-generated action items and follow-up recommendations

**Agent Management**
- Create and manage agent profiles
- Track individual agent performance over time
- View call history per agent

**Dashboard**
- Overview metrics (total calls, average scores, trends)
- Call listing with filtering and search
- Detailed call view with transcript and analysis
- Agent performance comparisons

## Architecture

The application consists of four main services:

```
Frontend (React)  -->  Backend (FastAPI)  -->  PostgreSQL
                              |
                              v
                           Redis
```

- **Frontend**: React single-page application served by Nginx in production
- **Backend**: FastAPI REST API handling business logic and external API calls
- **PostgreSQL**: Primary database for storing calls, agents, transcripts, and analysis
- **Redis**: Caching layer for improved performance

External services:
- **Replicate API**: Audio transcription using Whisper model
- **OpenRouter API**: LLM analysis using Gemini model

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, shadcn/ui, React Query |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Pydantic |
| Database | PostgreSQL 15 with asyncpg driver |
| Cache | Redis 7 |
| Containerization | Docker, Docker Compose |
| Testing | pytest, pytest-asyncio |

## Prerequisites

**For Docker deployment:**
- Docker Engine 20.10 or later
- Docker Compose v2.0 or later
- 4GB RAM minimum

**For local development:**
- Python 3.11
- Node.js 20
- PostgreSQL 15
- Redis 7

**Required API keys:**
- Replicate API key (https://replicate.com)
- OpenRouter API key (https://openrouter.ai)

## Running with Docker (Recommended)

This method runs all services (frontend, backend, database, redis) in containers.

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Call-Center-Audio-Intelligence
```

### Step 2: Configure Environment Variables

Copy the production environment template:

```bash
cp .env.production .env
```

Edit `.env` and add your API keys:

```bash
REPLICATE_API_KEY=your_replicate_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Step 3: Start the Application

Run the startup script:

```bash
chmod +x docker-start.sh
./docker-start.sh
```

This script will:
1. Build Docker images for frontend and backend
2. Start all containers (frontend, backend, db, redis)
3. Wait for services to be healthy
4. Run database migrations
5. Seed the database with sample data

### Step 4: Access the Application

Once the script completes:

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

### Docker Commands Reference

```bash
# View running containers
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# View logs for specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Stop all services
docker-compose -f docker-compose.prod.yml down

# Stop and remove volumes (deletes all data)
docker-compose -f docker-compose.prod.yml down -v

# Restart a specific service
docker-compose -f docker-compose.prod.yml restart backend

# Rebuild images after code changes
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

## Running Locally (Development)

This method runs the database and Redis in Docker while running the frontend and backend directly on your machine. This is useful for development because it supports hot reloading.

### Step 1: Clone and Setup

```bash
git clone <repository-url>
cd Call-Center-Audio-Intelligence
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys
REPLICATE_API_KEY=your_replicate_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# Database (localhost because DB runs in Docker with port exposed)
DATABASE_URL=postgresql+asyncpg://call_center:call_center_pw@localhost:5432/call_center_ai
REDIS_URL=redis://localhost:6379/0

# Database credentials (used by Docker)
POSTGRES_DB=call_center_ai
POSTGRES_USER=call_center
POSTGRES_PASSWORD=call_center_pw

# Application settings
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
```

### Step 3: Start Database and Redis

```bash
docker-compose -f docker-compose.db.yml up -d
```

Verify they are running:

```bash
docker-compose -f docker-compose.db.yml ps
```

### Step 4: Setup Backend

Create and activate a Python virtual environment:

```bash
python -m venv .venv

# On Linux/macOS
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Run database migrations:

```bash
cd backend
alembic upgrade head
cd ..
```

Seed the database with sample data (optional):

```bash
python -m backend.app.db.seed
```

Start the backend server:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at http://localhost:8000

### Step 5: Setup Frontend

Open a new terminal window.

Install Node.js dependencies:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will be available at http://localhost:5173

### Local Development URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| REPLICATE_API_KEY | API key for Replicate transcription service | Yes |
| OPENROUTER_API_KEY | API key for OpenRouter LLM service | Yes |
| DATABASE_URL | PostgreSQL connection string | Yes |
| REDIS_URL | Redis connection string | Yes |
| APP_ENV | Environment (development/production) | No |
| DEBUG | Enable debug mode (true/false) | No |
| LOG_LEVEL | Logging level (DEBUG/INFO/WARNING/ERROR) | No |
| CORS_ORIGINS | Allowed CORS origins (comma-separated) | No |

### Database Configuration

The database connection string format:

```
postgresql+asyncpg://username:password@host:port/database
```

For Docker deployment, use `db` as the host (Docker service name).
For local development, use `localhost` with port 5432 exposed.

## API Reference

### Health Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Basic health check |
| GET | /ready | Readiness check (includes DB connection) |

### Calls API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/calls | List all calls with optional filtering |
| GET | /api/calls/{id} | Get call details including transcript and analysis |
| POST | /api/calls/upload | Upload audio file for processing |
| DELETE | /api/calls/{id} | Delete a call |

### Agents API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/agents | List all agents |
| GET | /api/agents/{id} | Get agent details |
| POST | /api/agents | Create new agent |
| PUT | /api/agents/{id} | Update agent |
| DELETE | /api/agents/{id} | Delete agent |
| GET | /api/agents/{id}/performance | Get agent performance metrics |

### Dashboard API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/dashboard/overview | Get dashboard overview metrics |

Full API documentation with request/response schemas is available at `/docs` when the backend is running.

## Project Structure

```
Call-Center-Audio-Intelligence/
├── backend/
│   ├── app/
│   │   ├── api/                 # API route handlers
│   │   │   ├── agents.py        # Agent endpoints
│   │   │   ├── calls.py         # Call endpoints
│   │   │   └── dashboard.py     # Dashboard endpoints
│   │   ├── db/
│   │   │   ├── database.py      # Database connection setup
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   └── seed.py          # Database seeding script
│   │   ├── services/
│   │   │   ├── analysis.py      # LLM analysis service
│   │   │   └── transcription.py # Audio transcription service
│   │   ├── utils/
│   │   │   └── error_handling.py # Error handling utilities
│   │   ├── config.py            # Application configuration
│   │   ├── main.py              # FastAPI application entry point
│   │   └── schemas.py           # Pydantic schemas
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Backend tests
│   ├── Dockerfile               # Development Dockerfile
│   ├── Dockerfile.prod          # Production Dockerfile
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   │   └── ui/              # shadcn/ui components
│   │   ├── pages/               # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Calls.tsx
│   │   │   ├── CallDetail.tsx
│   │   │   ├── Agents.tsx
│   │   │   └── AgentDetail.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   └── utils.ts         # Utility functions
│   │   ├── App.tsx              # Root component
│   │   └── main.tsx             # Entry point
│   ├── Dockerfile               # Development Dockerfile
│   ├── Dockerfile.prod          # Production Dockerfile
│   ├── nginx.conf               # Nginx configuration for production
│   └── package.json             # Node.js dependencies
├── data/                        # Sample audio files for testing
├── scripts/
│   └── validate.sh              # Health check validation script
├── docker-compose.yml           # Basic Docker Compose
├── docker-compose.prod.yml      # Production Docker Compose
├── docker-compose.dev.yml       # Development Docker Compose
├── docker-compose.db.yml        # Database-only Docker Compose
├── docker-start.sh              # Docker startup script
├── .env.production              # Production environment template
└── README.md                    # This file
```

## Testing

### Running Backend Tests

```bash
cd backend
pytest tests/ -v
```

With coverage report:

```bash
pytest tests/ -v --cov=app --cov-report=html
```

### Test Categories

- `test_api_endpoints.py`: API integration tests
- `test_transcription.py`: Transcription service tests
- `test_analysis.py`: Analysis service tests

## Troubleshooting

### Docker Issues

**Port already in use:**

```bash
# Check what is using the port
lsof -i :8000
lsof -i :5432

# Stop conflicting services or change ports in docker-compose.prod.yml
```

**Container fails to start:**

```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs backend

# Check container status
docker-compose -f docker-compose.prod.yml ps
```

**Database connection refused:**

Ensure the database container is healthy before the backend starts. The docker-compose files include health checks, but if running manually, wait for PostgreSQL to be ready.

### Local Development Issues

**Backend cannot connect to database:**

1. Verify PostgreSQL container is running: `docker-compose -f docker-compose.db.yml ps`
2. Check DATABASE_URL uses `localhost` (not `db`)
3. Verify port 5432 is exposed and not blocked

**Frontend cannot reach backend:**

1. Verify backend is running on port 8000
2. Check browser console for CORS errors
3. Ensure CORS_ORIGINS includes `http://localhost:5173`

**Module not found errors:**

1. Ensure virtual environment is activated
2. Run `pip install -r backend/requirements.txt`
3. For frontend: `cd frontend && npm install`

### API Key Issues

**Transcription fails:**

- Verify REPLICATE_API_KEY is set correctly
- Check Replicate dashboard for API usage limits
- Review backend logs for specific error messages

**Analysis fails:**

- Verify OPENROUTER_API_KEY is set correctly
- Check OpenRouter dashboard for API credits
- Review backend logs for specific error messages