# Lenny Growth Assistant

A specialized growth assistant built for the Forward Deployed Engineer take-home assignment. This application provides grounded insights from Lenny's Podcast transcripts with strict evidence-based responses and citation support.

## Features

- **Grounded Q&A**: All responses are grounded in Lenny's Podcast transcripts with proper citations
- **Real-time Streaming**: SSE-based streaming responses for smooth user experience
- **Content Generation**: Ship 30 for 30 essays, LinkedIn posts, X threads, and concise insights
- **Session Management**: Persistent conversation sessions with history
- **Markdown Support**: Rich text rendering with proper formatting
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Architecture

The application consists of:

- **Backend**: FastAPI service with RAG retrieval, grounding, and LLM integration
- **Frontend**: React + Vite application with SSE streaming and modern UI
- **Ingestion**: Data processing pipelines for transcript ingestion and evaluation

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (or use Docker)
- Anthropic API key or Ollama for local LLM

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the backend server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults to /api for proxied requests)
   ```

4. **Start the development server**:
   ```bash
   npm run dev
   ```

5. **Open your browser**:
   Navigate to `http://localhost:5173`

### Using Docker

Alternatively, use Docker Compose for quick setup:

```bash
docker-compose up -d
```

This will start PostgreSQL, the backend API, and the frontend development server.

## Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/lenny_growth

# LLM Provider
LLM_PROVIDER=anthropic  # or "ollama"
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Ollama (if using local provider)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# RAG Settings
RAG_RELEVANCE_DISTANCE_THRESHOLD=0.35
CONVERSATION_HISTORY_LIMIT=10
MODEL_TIMEOUT_SECONDS=60.0

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=5173

# CORS
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

### Frontend (.env)

```bash
VITE_API_BASE_URL=/api  # Uses Vite proxy to backend
# Or direct: VITE_API_BASE_URL=http://localhost:8000/api
```

## SSE Integration

The frontend uses Server-Sent Events (SSE) for real-time streaming of assistant responses. The SSE contract defines three event types:

### SSE Event Types

1. **token**: Streamed content tokens
   ```json
   {
     "event": "token",
     "data": {
       "delta": "Hello "
     }
   }
   ```

2. **done**: Successful completion (including grounded refusals)
   ```json
   {
     "event": "done",
     "data": {
       "message_id": "uuid",
       "citations": [...],
       "status": "completed",
       "skill": "chat",
       "content_type": null
     }
   }
   ```

3. **error**: System/infrastructure failures
   ```json
   {
     "event": "error",
     "data": {
       "code": "MODEL_UNAVAILABLE",
       "message": "Model failed to generate"
     }
   }
   ```

### Critical SSE Semantics

**`done` = request completed successfully, including grounded refusal**

A grounded refusal caused by insufficient/no eligible retrieval evidence is a SUCCESSFUL assistant response. It arrives via the `done` event with:
- Refusal text as assistant message content
- Empty citations array
- NOT an error event

**`error` = actual system/provider/infrastructure failure**

The `error` event is reserved for actual system failures:
- Ollama unavailable
- Missing Anthropic API key
- Model timeout
- Provider/API failure
- Database failure
- Unrecoverable server failure

## Session Handling

The frontend automatically manages session persistence:

1. **Session Creation**: Automatically creates a new session on first load
2. **Session Persistence**: Session ID stored in localStorage
3. **Session Recovery**: Attempts to recover existing session on reload
4. **Session Isolation**: All messages are scoped to their respective sessions

## Supported Content Actions

The frontend provides quick action buttons that route through backend-authoritative skills:

- **Ship 30 Essay**: Generates long-form essays (~1,250 words) with Ship 30 for 30 principles
- **LinkedIn Post**: Creates LinkedIn-style posts (150-300 words)
- **X Thread**: Generates Twitter/X threads (5-10 posts)
- **Concise Insight**: Produces brief product/growth insights (80-150 words)

These actions use the existing backend Ship30 skill routing system and do not duplicate generation logic in the frontend.

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

Expected: 111/111 tests passing

### Frontend Tests

```bash
cd frontend
npm test -- --run
```

### Frontend Build

```bash
cd frontend
npm run build
```

## Development

### Backend Development

- **API Documentation**: Available at `http://localhost:8000/docs` when backend is running
- **Database Migrations**: Use Alembic for schema changes
- **Logging**: Check backend logs for detailed request/response information

### Frontend Development

- **Hot Module Replacement**: Vite provides instant updates during development
- **API Proxy**: Vite proxies `/api` requests to backend at `http://localhost:8000`
- **TypeScript**: Full TypeScript support with strict type checking

## Grounding and Citation

All assistant responses are grounded in retrieved transcript evidence:

- **Citations**: Each response includes episode title, guest name, and source URL
- **Evidence-Based**: Responses only use information from retrieved chunks
- **Refusal Handling**: When no relevant evidence is found, the assistant politely refuses rather than hallucinating
- **Security**: Prompt injection boundaries prevent transcript content from overriding system instructions

## Repository Structure

```
lenny-growth-assistant/
├── backend/               # FastAPI backend service
│   ├── app/
│   │   ├── api/          # API routes (sessions, retrieval, health)
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic (agent, retrieval, LLM)
│   │   ├── skills/       # Specialized skills (Ship30)
│   │   └── main.py       # FastAPI application entry
│   ├── tests/            # Backend test suite
│   └── requirements.txt   # Python dependencies
├── frontend/             # React + Vite frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── lib/          # API client and utilities
│   │   └── types/        # TypeScript type definitions
│   └── package.json      # Node dependencies
├── ingestion/            # Data ingestion and evaluation
│   └── scripts/          # Ingestion and evaluation scripts
├── docs/                 # Architecture documentation
└── README.md            # This file
```

## Troubleshooting

### Backend Issues

- **Database Connection**: Ensure PostgreSQL is running and credentials are correct
- **LLM Provider**: Check API key configuration and provider availability
- **CORS Errors**: Verify CORS origins include your frontend URL

### Frontend Issues

- **API Connection**: Ensure backend is running and accessible
- **Build Errors**: Clear node_modules and reinstall dependencies
- **TypeScript Errors**: Check type definitions and imports

## License

This project is part of a take-home assignment and is intended for demonstration purposes.