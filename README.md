# Signal Clone

A real-time messaging application inspired by Signal, built as a full-stack software engineering project with a clean, layered architecture.

---

## 1. Project Overview

This application delivers the core communication experience of Signal:
- **Instant 1-on-1 and Group Messaging**: Low-latency message delivery using WebSocket connections.
- **Message Receipts**: Accurate tracking of `SENT` (single check), `DELIVERED` (double check), and `READ` (sky-blue double check) statuses.
- **Presence & Typing**: Real-time typing indicators and live online/last-seen timestamps.
- **Signal-Inspired Design**: Clean, messaging-focused layout built with Tailwind CSS, distinct message bubbles, unread previews, and full responsive mobile navigation.
- **Stateless Authentication**: JWT Bearer token sessions, registration, login, and simulated OTP verification.
- **Layered Architecture**: Decoupled Router → Service → Repository design on the backend and TanStack Query + Zustand on the frontend.

*Note: In accordance with the project scope, End-to-End Encryption (E2EE) is simulated rather than cryptographically implemented so the focus remains on architecture, real-time synchronization, and data modeling.*

---

## 2. Implemented Features

| Feature | Description | Status |
|---|---|---|
| **User Registration & Mocked OTP** | Register with username/phone, password, and mocked OTP verification (`123456`) | ✅ Complete |
| **Stateless JWT Authentication** | Secure token-based session persistence stored in `localStorage` | ✅ Complete |
| **User Profiles** | Profile display name, avatar, online status, and last seen timestamps | ✅ Complete |
| **Contact Management** | Search all registered users, add contacts, and view contact directory | ✅ Complete |
| **Direct (1-on-1) Conversations** | Deduplicated direct conversations between users with membership checks | ✅ Complete |
| **Group Conversations** | Create group chats, multi-user membership, and admin permissions | ✅ Complete |
| **Real-time Messaging** | Instant message broadcast via authenticated WebSocket connections | ✅ Complete |
| **Message Persistence** | SQLite database storage with chronological history and pagination | ✅ Complete |
| **Receipt Tracking** | `SENT` → `DELIVERED` → `READ` state transitions per recipient | ✅ Complete |
| **Typing Indicators** | Throttled `typing.started` and `typing.stopped` events with animated bubble | ✅ Complete |
| **Online Presence** | Automatic presence updates upon connect and disconnect with last-seen | ✅ Complete |
| **Signal-Inspired UI/UX** | Dark charcoal aesthetic, Signal blue accents, distinct bubbles, inline ticks | ✅ Complete |
| **Responsive Mobile Layout** | Full-width conversation list and dedicated chat area with back navigation | ✅ Complete |
| **Database Seeding** | Deterministic, idempotent seed script (`backend/seed.py`) | ✅ Complete |

---

## 3. Tech Stack

### Frontend
- **Framework**: Next.js 14+ (App Router, Turbopack)
- **Language**: TypeScript (Strict mode)
- **Styling**: Tailwind CSS with custom design tokens
- **State Management**: TanStack Query (Server State / Cache) & Zustand (Client Auth Store)
- **Icons**: Lucide React
- **Network**: Native WebSocket client with exponential backoff & Fetch API

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ASGI Server**: Uvicorn
- **ORM**: SQLAlchemy 2.0 (Async)
- **Database**: SQLite with Write-Ahead Logging (WAL) via `aiosqlite`
- **Data Modeling & Validation**: Pydantic v2
- **Authentication**: JWT (`python-jose`) and password hashing (`passlib[bcrypt]`)
- **Testing**: `pytest` & `pytest-asyncio` with in-memory `StaticPool` SQLite

---

## 4. Repository Structure

```
signal-clone/
├── frontend/
│   ├── app/                  # Next.js App Router (pages and layouts)
│   ├── components/           # Reusable UI components
│   ├── hooks/                # useWebSocket custom React hook
│   ├── lib/                  # API client, WebSocket client, Query provider
│   ├── services/             # HTTP service functions (auth, contacts, conversations)
│   ├── stores/               # Zustand authentication store
│   └── types/                # Strict TypeScript interfaces matching backend models
│
├── backend/
│   ├── app/
│   │   ├── core/             # Config, database engine, security utilities
│   │   ├── models/           # SQLAlchemy ORM models (User, Message, Conversation, etc.)
│   │   ├── schemas/          # Pydantic DTOs for requests and responses
│   │   ├── repositories/     # Data access layer (pure SQL/ORM logic)
│   │   ├── services/         # Business logic layer
│   │   ├── routers/          # API endpoints (auth, users, contacts, conversations, ws)
│   │   ├── websocket/        # ConnectionManager connection tracking
│   │   └── main.py           # FastAPI application entrypoint
│   ├── tests/                # Comprehensive pytest suite
│   ├── seed.py               # Database seed script
│   └── requirements.txt      # Python dependencies
│
├── docs/                     # Architecture, database schema, and API documentation
│   ├── architecture.md
│   ├── database.md
│   └── api.md
├── docker-compose.yml        # Container orchestration
└── README.md                 # Project documentation
```

---

## 5. Setup & Running Locally

### Prerequisites
- **Node.js**: v20 or higher
- **Python**: v3.11, v3.12, or v3.13
- **Git**

### Backend Setup

```bash
cd backend

# 1. Create and activate a virtual environment
# Windows:
python -m venv venv
.\venv\Scripts\activate
# macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment file
cp .env.example .env

# 4. Optional: Seed demo data (Alice, Bob, Charlie)
python seed.py

# 5. Start development server
uvicorn app.main:app --reload --port 8000
```
Backend API will be running at `http://localhost:8000`.  
Swagger documentation is available at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Configure environment variables (if different from defaults)
# Default points to http://localhost:8000 and ws://localhost:8000/ws

# 3. Start development server
npm run dev
```
Frontend application will be accessible at `http://localhost:3000`.

---

## 6. Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy async database connection URI | `sqlite+aiosqlite:///./signal_clone.db` |
| `JWT_SECRET` | Secret key used to sign and verify JWT tokens | `super-secret-jwt-key-change-in-production` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of issued access tokens | `1440` (24 hours) |
| `CORS_ORIGINS` | JSON list of allowed origins | `["http://localhost:3000"]` |
| `DEBUG` | Toggle debug output | `True` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the backend REST API | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL for real-time messaging | `ws://localhost:8000/ws` |

---

## 7. Architecture Overview

The system follows a strict three-tier layered architecture:

```
[ Frontend: Next.js + TanStack Query + Zustand ]
                     │
       ┌─────────────┴─────────────┐
  REST (HTTP)                 WebSocket (WS)
       │                           │
[ FastAPI Routers ]      [ WebSocket Endpoint ]
       │                           │
       ├───────────────────────────┘
       ▼
[ Services Layer (Business Logic & Authorization) ]
       │
[ Repositories Layer (SQLAlchemy ORM Data Access) ]
       │
[ SQLite Database (WAL Mode + busy_timeout) ]
```

### Key Architectural Highlights:
1. **Scoped WebSocket Sessions**: The WebSocket endpoint uses short-lived database sessions (`async with async_session_factory() as session:`) for handshake authentication, typing membership checks, and receipts. Sessions are never held open across network frame waits, preventing SQLite transaction locks.
2. **SQLite WAL Mode**: Configured with `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`, enabling concurrent reads while writes are occurring.
3. **Receipt Lifecycle**: Every message creates per-recipient `MessageReceipt` entities. If the recipient is online, the receipt is marked `DELIVERED` immediately; if offline, it starts as `SENT` and transitions to `DELIVERED` upon connection. When the recipient views the chat, receipts transition to `READ`.
4. **Resilient WebSocket Client**: Frontend features deduplicated socket connection handling, automatic exponential backoff reconnection, and a 25-second ping heartbeat.

---

## 8. Database Schema Overview

Refer to [docs/database.md](docs/database.md) for full relational details.
- **`users`**: User identity, credentials (`password_hash`), presence (`is_online`), and `last_seen`.
- **`contacts`**: Unidirectional contact association between users with self-contact check constraint.
- **`conversations`**: Polymorphic conversation table supporting both `DIRECT` and `GROUP` conversations.
- **`conversation_members`**: Junction table tracking user participation, roles (`ADMIN`, `MEMBER`), and join dates.
- **`messages`**: Message content, conversation association, timestamp, and optional parent message for replies.
- **`message_receipts`**: Per-recipient status tracking (`SENT`, `DELIVERED`, `READ`) with unique constraint on `(message_id, user_id)`.

---

## 9. API & WebSocket Summary

### REST Endpoints
- `POST /auth/register` — Register a new account
- `POST /auth/verify` — Verify registration OTP
- `POST /auth/login` — Log in and receive JWT token
- `GET /auth/me` — Retrieve current user profile
- `GET /users/search?q={query}` — Search users by username/display name
- `GET /contacts` & `POST /contacts` — Retrieve and add contacts
- `GET /conversations` — List conversations with latest message previews
- `POST /conversations/direct` — Get or create a 1-on-1 chat
- `POST /conversations/group` — Create a group chat with member IDs
- `GET /conversations/{id}/messages` — Paginated message history
- `POST /conversations/{id}/messages` — Send a message
- `POST /conversations/{id}/read` — Mark unread messages as read
- `GET /health` — Service health check

### WebSocket Events (`/ws?token=<JWT>`)
- `typing.started` & `typing.stopped` — Ephemeral typing notification
- `message.created` — Broadcast when a new message is posted
- `message.delivered` — Broadcast when messages are delivered to an online recipient
- `message.read` — Broadcast when messages are read by the recipient
- `presence.updated` — Broadcast when a user connects or disconnects
- `ping` & `pong` — Heartbeat liveness checks

See [docs/api.md](docs/api.md) for complete payload documentation.

---

## 10. Important Assumptions

1. **Simulated OTP**: Phone verification OTP is mocked with code `123456` to avoid external SMS gateway dependencies.
2. **Simulated E2EE**: In line with the assignment guidelines, messages are transferred and stored in plaintext; Signal's Double Ratchet / Signal Protocol is not implemented.
3. **Single-Node WebSocket**: The WebSocket manager holds connections in memory, suitable for SQLite and single-instance deployments. For horizontal scaling across multiple instances, Redis Pub/Sub would be used.
4. **SQLite Concurrency**: SQLite with WAL mode is used for simple zero-dependency local setup. For high-scale production usage, PostgreSQL is recommended.

---

## 11. Testing Instructions

### Running Backend Tests
Execute the full pytest test suite from the `backend/` directory:
```bash
cd backend
.\venv\Scripts\pytest.exe
```
**Expected Result**: All 34 tests passing across auth, database models, permissions, receipts, and conversations.

### Running Frontend Production Build
Validate TypeScript types and Next.js bundle compilation:
```bash
cd frontend
npm run build
```
**Expected Result**: Successful build compilation with 0 TypeScript or linting errors.

### Manual Cross-Browser Live Testing
1. Open Chrome window 1 at `http://localhost:3000` and register/log in as user **Alice**.
2. Open Chrome incognito window 2 at `http://localhost:3000` and register/log in as user **Bob**.
3. Alice searches for Bob and starts a conversation.
4. Verify typing indicators: typing in Alice's box displays "typing…" in Bob's header and conversation list.
5. Alice sends a message: Bob receives it instantly via WebSocket without page refresh.
6. Check receipt ticks: Alice's bubble displays double check `✓✓`.
7. Once Bob focuses on the conversation, the tick marks turn bright blue (`READ`).
8. Refresh both windows: all messages and latest previews remain persisted.
