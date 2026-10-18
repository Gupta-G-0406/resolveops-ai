
# ResolveOps AI

### Multi-Agent Customer Support Investigation Platform

ResolveOps AI is an AI-powered customer support investigation system that analyzes order-related complaints using multiple specialized AI agents, business tools, and retrieval-augmented generation.

The system helps support teams investigate complaints using order, payment, shipment, and company policy evidence.

## Key Features

- Multi-agent investigation workflow using LangGraph
- Groq-powered LLM reasoning
- Dynamic supervisor and specialist agent routing
- MCP tools for business data retrieval
- Agentic RAG with ChromaDB for policy retrieval
- Evidence verification and investigation reports
- PostgreSQL investigation history and audit events
- Background recovery worker for interrupted investigations
- React and TypeScript operations dashboard
- Investigation filters, pagination, and ticket navigation

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI, Python |
| AI Orchestration | LangGraph |
| LLM | Groq |
| Tool Integration | Model Context Protocol (MCP) |
| Retrieval | Agentic RAG, ChromaDB |
| Database | PostgreSQL |
| Infrastructure | Docker Compose |

## Architecture

```text
                 React + TypeScript
                  Operations UI
                        |
                        v
                  FastAPI Backend
                        |
                        v
                LangGraph Supervisor
                        |
             +----------+----------+
             |          |          |
             v          v          v
         Order Agent  Shipment   Policy Agent
                      Agent
             |          |          |
             v          v          v
         MCP Tools   MCP Tools   Agentic RAG
             |          |          |
             +----------+----------+
                        |
                        v
              Evidence Verification
                        |
                        v
              Investigation Report
                        |
                        v
                PostgreSQL Storage
                        |
                        v
              Audit Trail & History
```

## How It Works

1. A support agent selects a customer support ticket.
2. The backend loads ticket and order context.
3. A LangGraph supervisor selects relevant specialist agents.
4. Business agents retrieve information using MCP tools.
5. The policy agent retrieves relevant company policies through Agentic RAG.
6. Evidence is verified and an investigation report is generated.
7. Investigation records and audit events are stored in PostgreSQL.
8. The frontend displays the report, evidence, verification, and history.

## Project Structure

```text
ResolveOps AI/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── db/
│   │   ├── services/
│   │   └── ...
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── types/
├── docker-compose.yml
└── README.md
```

Directory names are illustrative and should be aligned with the actual repository before publishing.

## Local Development

### Prerequisites

- Python
- Node.js and npm
- Docker Desktop
- PostgreSQL (via Docker Compose)
- Groq API key

### 1. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d
```

### 2. Start the backend

```powershell
cd backend

.\.venv\Scripts\Activate.ps1

uvicorn app.main:app --reload
```

Backend API:

http://127.0.0.1:8000

FastAPI documentation:

http://127.0.0.1:8000/docs

### 3. Start the frontend

Open a new terminal:

```powershell
cd frontend

npm install

npm run dev
```

Frontend:

http://localhost:5173

### 4. Build and lint

```powershell
cd frontend

npm run build

npm run lint
```

### 5. Run backend tests

Activate the backend environment and run:

```powershell
python -m pytest
```

The backend environment variables, database migrations, seed data, and recovery worker must be configured according to the project's actual setup.

## Investigation API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/tickets` | List support tickets |
| GET | `/api/tickets/{id}` | Retrieve ticket details |
| POST | `/api/tickets/{id}/investigate` | Run AI investigation |
| GET | `/api/tickets/{id}/investigations` | Ticket investigation history |
| GET | `/api/investigations` | Paginated global history |
| GET | `/api/investigations/{id}` | Investigation details |
| GET | `/api/investigations/{id}/audit-events` | Audit events |

## Reliability

The backend includes investigation ownership leases, heartbeat handling, fencing checks, and a recovery worker to handle interrupted investigation execution.

## Safety

ResolveOps AI is a decision-support system.

AI-generated findings require appropriate human review. The application does not automatically issue refunds or perform financial transactions.

Demo policies and business records may be synthetic.

## Development Status

- Backend unit and integration tests previously passed
- Frontend production build passed
- Frontend lint passed with zero errors and warnings
- Browser end-to-end verification pending

## Future Improvements

- Authentication and role-based access control
- Real-time investigation progress streaming
- Automated browser end-to-end tests
- Deployment and monitoring
- Evaluation datasets for investigation accuracy

## License

Add a license before publishing if you intend to grant reuse rights.
