# Signal Clone — Project Overview Report

> A full-stack Signal-inspired messaging application built as a learning/interview-ready project.

---

## 1. Project at a Glance

| Property | Details |
|---|---|
| **Type** | Full-stack web application (messaging/chat) |
| **Inspiration** | Signal messenger |
| **Architecture** | REST API + WebSocket, client-server |
| **Deployment** | Docker Compose (dev), containerized |
| **Database** | SQLite (dev) → PostgreSQL-ready |
| **Auth** | Phone/username + OTP + JWT |

---

## 2. Tech Stack Overview

### 🐍 Backend
| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Framework** | FastAPI | 0.115.6 | Async web framework, REST + WebSocket |
| **Server** | Uvicorn (standard) | 0.34.0 | ASGI server with WebSocket support |
| **Database ORM** | SQLAlchemy | 2.0.36 | Async ORM (2.x style) |
| **DB Driver** | aiosqlite | 0.20.0 | Async SQLite adapter |
| **Database** | SQLite | (built-in) | File-based relational DB for dev |
| **Migrations** | Alembic | 1.14.1 | Schema migration management |
| **Validation** | Pydantic | 2.10.4 | Request/response DTO validation |
| **Config** | pydantic-settings | 2.7.1 | Env-var-driven configuration |
| **Auth (JWT)** | python-jose[cryptography] | 3.3.0 | JWT encode/decode |
| **Password Hash** | passlib[bcrypt] | 1.7.4 | Bcrypt password hashing |
| **Env Loading** | python-dotenv | 1.0.1 | `.env` file support |
| **WebSockets** | websockets | 14.2 | WebSocket protocol library |
| **Testing** | pytest + pytest-asyncio | 8.3.4 / 0.25.0 | Async test runner |
| **HTTP Testing** | httpx | 0.28.1 | Async HTTP test client |

### ⚛️ Frontend
| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Framework** | Next.js | 16.4.0 | React meta-framework (App Router) |
| **UI Library** | React | 19.3.0 | Component rendering |
| **Language** | TypeScript | ^5 | Static typing throughout |
| **Server State** | TanStack Query (React Query) | ^5.104.1 | Caching, fetching, sync |
| **Client State** | Zustand | ^5.0.15 | Auth token, user identity store |
| **Icons** | Lucide React | ^1.52.0 | Icon library |
| **Styling** | Tailwind CSS | ^4 | Utility-first CSS |
| **Linting** | ESLint + eslint-config-next | ^9 / 16.4.0 | Code quality |

### 🐳 Infrastructure
| Tool | Purpose |
|---|---|
| **Docker** | Container runtime |
| **Docker Compose** | Multi-service orchestration (backend + frontend) |
| **Alembic** | DB migration pipeline |

---

## 3. Backend Architecture — Deep Dive

### Layered Pattern: Router → Service → Repository
```
HTTP/WS Request
      ↓
   Routers  (HTTP concerns: status codes, auth headers)
      ↓
  Services  (Business logic: pure, no HTTP/DB knowledge)
      ↓
Repositories  (Data access: SQLAlchemy queries only)
      ↓
  SQLAlchemy  (Async ORM)
      ↓
   SQLite DB
```

### Backend Directory Structure
```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point, CORS, router mounting
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings (lru_cache singleton)
│   │   ├── database.py      # Async SQLAlchemy engine + session factory
│   │   ├── deps.py          # FastAPI dependency injection (get_db, get_current_user)
│   │   └── security.py      # JWT creation/decode, bcrypt hashing
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── contact.py
│   │   ├── conversation.py
│   │   ├── conversation_member.py
│   │   ├── message.py
│   │   └── message_receipt.py
│   ├── schemas/             # Pydantic request/response DTOs
│   ├── routers/             # FastAPI route handlers
│   │   ├── auth.py          # Register, login, OTP verify
│   │   ├── users.py         # User profile CRUD
│   │   ├── contacts.py      # Add/list contacts
│   │   ├── conversations.py # CRUD + message history
│   │   ├── websocket.py     # WS connect/disconnect/event routing
│   │   └── health.py        # /health endpoint
│   ├── services/            # Business logic
│   │   ├── auth.py          # Registration, OTP, token issuance
│   │   ├── contact.py       # Contact management logic
│   │   └── conversation.py  # Message send, receipt update
│   ├── repositories/        # DB query layer
│   │   ├── user.py
│   │   ├── contact.py
│   │   └── conversation.py  # Paginated messages, member lookups
│   └── websocket/
│       └── manager.py       # ConnectionManager: in-memory WS connection pool
├── migrations/
│   └── versions/
│       └── 00c06c708ed0_initial_schema.py   # Single initial migration
├── tests/                   # pytest test suite
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_database.py
│   ├── test_health.py
│   ├── test_phase3.py
│   ├── test_phase5a.py
│   └── test_phase5b.py
├── seed.py                  # Idempotent seed: Alice, Bob, Charlie + conversations
├── requirements.txt
├── Dockerfile
└── alembic.ini
```

### API Endpoints
| Router | Key Endpoints |
|---|---|
| **auth** | `POST /auth/register`, `POST /auth/login`, `POST /auth/verify-otp` |
| **users** | `GET /users/me`, `PATCH /users/me`, user lookup |
| **contacts** | `GET /contacts`, `POST /contacts` |
| **conversations** | `GET /conversations`, `POST /conversations`, `GET /conversations/{id}/messages` |
| **websocket** | `WS /ws/{user_id}` |
| **health** | `GET /health` |

### WebSocket Events
| Event | Direction | Purpose |
|---|---|---|
| `new_message` | Bidirectional | Real-time message delivery |
| `typing` / `typing.started` / `typing.stopped` | Client → Server → Members | Ephemeral, not persisted |
| `message_delivered` / `message.delivered` | Server → Sender | Delivery confirmation |
| `message_read` / `message.read` | Server → Sender | Read receipt |
| `user_online` / `user_offline` / `presence.updated` | Server → All | Online/offline presence |
| `pong` | Server → Client | Keepalive response |

---

## 4. Database Schema

### Entity Relationship
```
User ──┬──< Contact
       ├──< ConversationMember >──── Conversation ──< Message ──< MessageReceipt
       ├──< Message (sender)                                 ↑
       └──< MessageReceipt                              (self-ref reply_to)
```

### Tables

| Table | Key Columns | Notes |
|---|---|---|
| `users` | id (UUID PK), username, phone, display_name, avatar_url, password_hash, is_online, last_seen | UUID PKs for security + portability |
| `contacts` | id, user_id → users, contact_user_id → users | Unidirectional. UniqueConstraint prevents duplicates. CheckConstraint prevents self-contact |
| `conversations` | id, type (DIRECT\|GROUP), name, avatar_url, created_by_id | Single table for both DMs and groups |
| `conversation_members` | id, conversation_id, user_id, role (MEMBER\|ADMIN), joined_at, left_at | left_at tombstone for soft-leave tracking |
| `messages` | id, conversation_id, sender_id, content, message_type (TEXT\|IMAGE\|FILE\|SYSTEM), reply_to_message_id | Self-referencing FK for reply threads |
| `message_receipts` | id, message_id, user_id, status (SENT\|DELIVERED\|READ), timestamp | Per-recipient tracking enables group read receipts |

> **Key Design Choice**: One `conversations` table handles both direct + group chats via a `type` discriminator. This keeps the message/receipt engine uniform.

---

## 5. Frontend Architecture — Deep Dive

### Directory Structure
```
frontend/
├── app/                     # Next.js App Router pages
│   ├── layout.tsx           # Root layout with query provider
│   ├── page.tsx             # Main chat page (conversations + messages)
│   ├── login/               # Login page
│   ├── register/            # Registration page
│   ├── verify-otp/          # OTP verification page
│   └── onboarding/          # Post-registration onboarding
├── components/
│   ├── chat/                # Chat window components
│   ├── contacts/            # Contact list components
│   ├── conversations/       # Conversation list
│   ├── groups/              # Group management
│   ├── settings/            # Profile/settings panel
│   └── ui/                  # Reusable base UI primitives
├── hooks/
│   └── use-websocket.ts     # Custom hook: WS connection lifecycle
├── lib/
│   ├── api-client.ts        # Centralized fetch wrapper (auth headers, base URL)
│   ├── ws-client.ts         # WebSocket singleton with reconnection logic
│   └── query-provider.tsx   # TanStack Query provider wrapper
├── services/                # API call functions (used in TanStack Query)
│   ├── auth.ts
│   ├── contacts.ts
│   └── conversations.ts
├── stores/
│   └── auth-store.ts        # Zustand store: access_token + current user
├── types/
│   └── index.ts             # TypeScript interfaces mirroring backend Pydantic schemas
└── next.config.ts
```

### State Management Split
| What | Tool | Why |
|---|---|---|
| Messages, conversations, contacts | **TanStack Query** | Server state — handles caching, staleness, refetching |
| Auth token + current user identity | **Zustand** | Client state — lightweight, no over-engineering |
| Real-time events | **WebSocket Client singleton** | Custom reconnect, event dispatch |

### Key Architectural Patterns
- **No direct `fetch()` in components** — all calls go through `api-client.ts`
- **Single WebSocket singleton** (`ws-client.ts`) manages reconnection, event listeners
- **Types mirror Pydantic schemas** — `types/index.ts` is the single source of truth for shapes
- **Services layer** between TanStack Query hooks and the API client

---

## 6. Authentication Flow

```
1. POST /auth/register → user created, OTP "sent" (mocked as 123456)
2. POST /auth/verify-otp → OTP verified → JWT access token returned
3. POST /auth/login → username/phone + password → JWT returned
4. All subsequent requests: Authorization: Bearer <JWT>
5. WS connect: token passed as query param ws://host/ws/{user_id}?token=...
```

> OTP is **mocked** (fixed code `123456`) — no real SMS gateway is wired.

---

## 7. Real-Time Message Flow

### Direct Message
```
Sender → WS: new_message → Server persists → Server fans out to recipient's WS
Recipient online → Server → WS: message_delivered → Sender
Recipient reads → WS: message_read → Server updates receipt → Sender
```

### Group Message
Same flow but **N receipts** are created (one per member) and fanned out to all **N online members** independently.

---

## 8. Testing Setup

| File | Coverage |
|---|---|
| `test_health.py` | Health endpoint smoke test |
| `test_auth.py` | Register, login, OTP verify flows |
| `test_database.py` | Model creation and DB session integrity |
| `test_phase3.py` | Contacts + conversations CRUD |
| `test_phase5a/b.py` | Message sending, receipts, WebSocket behavior |

- **Framework**: `pytest` + `pytest-asyncio`  
- **HTTP client**: `httpx` (async-compatible)  
- **Test DB**: Separate in-memory/temp SQLite instance via `conftest.py`

---

## 9. Configuration & Environment

### Backend `.env` variables
| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./signal_clone.db` | DB connection string |
| `JWT_SECRET` | `CHANGE-ME-IN-PRODUCTION` | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |

### Frontend `.env.local` variables
| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend REST base URL |
| `NEXT_PUBLIC_WS_URL` | Backend WebSocket base URL |

---

## 10. Docker Compose Setup

| Service | Port | Command |
|---|---|---|
| `backend` | `8000` | `uvicorn app.main:app --reload` |
| `frontend` | `3000` | `npm run dev` |

Both services mount local volumes for hot-reload in development. Frontend depends on backend.

---

## 11. Seed Data

[`seed.py`](file:///d:/Projects/Signal%20Clone/backend/seed.py) creates a deterministic, idempotent dev dataset:
- **Users**: Alice, Bob, Charlie, Diana, Eve (with bcrypt-hashed passwords)
- **Contacts**: Cross-contact relationships established
- **Conversations**: Several direct + group conversations
- **Messages**: Representative conversation history inserted

Running it multiple times is safe — it checks for existence before creating.

---

## 12. Scalability Roadmap (as documented)

| Concern | Current | Planned Upgrade |
|---|---|---|
| Database | SQLite | PostgreSQL |
| WebSocket scaling | In-memory `ConnectionManager` | Redis pub/sub |
| File storage | Not implemented | S3 / object storage |
| Background tasks | None | Celery / ARQ |
| Caching | TanStack Query only | Server-side Redis |
| Deployment | Docker Compose | Kubernetes / cloud-native |
| Rate limiting | None | FastAPI middleware |

---

## 13. Key Design Decisions

1. **Layered backend** — Router/Service/Repository makes each layer independently testable
2. **UUID primary keys** — Prevents sequential enumeration, enables future offline client-side ID generation
3. **Single conversations table** — Handles DIRECT and GROUP via a `type` discriminator; avoids table-per-type inheritance
4. **Per-member message receipts** — `MessageReceipt` junction table enables per-user `SENT/DELIVERED/READ` state in groups
5. **Async SQLAlchemy** — Keeps FastAPI's event loop non-blocking
6. **TanStack Query + Zustand split** — Server state vs client state separation avoids over-engineering a global store
7. **Centralized API + WS clients** — One file to update when backend URL changes; no component ever calls `fetch()` directly
8. **Soft-leave tombstone** — `left_at` column on `ConversationMember` preserves membership history

---

*Generated from analysis of the Signal Clone project at `d:\Projects\Signal Clone`*
