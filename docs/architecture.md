# System Architecture

## 1. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          Client (Browser)                        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │               Next.js (React + TypeScript)              │     │
│  │                                                         │     │
│  │  ┌───────────┐  ┌──────────┐  ┌───────────┐           │     │
│  │  │ Components │  │  Stores  │  │  Hooks    │           │     │
│  │  └─────┬─────┘  └────┬─────┘  └─────┬─────┘           │     │
│  │        │              │              │                   │     │
│  │        └──────────────┼──────────────┘                   │     │
│  │                       │                                  │     │
│  │              ┌────────┴────────┐                         │     │
│  │              │    Services     │                         │     │
│  │              └───┬─────────┬───┘                         │     │
│  │                  │         │                              │     │
│  │          ┌───────┴──┐  ┌──┴────────┐                    │     │
│  │          │API Client│  │ WS Client │                    │     │
│  │          └───┬──────┘  └──┬────────┘                    │     │
│  └──────────────┼────────────┼─────────────────────────────┘     │
│                 │            │                                    │
└─────────────────┼────────────┼────────────────────────────────────┘
                  │ REST       │ WebSocket
                  │ (HTTP)     │ (WS)
┌─────────────────┼────────────┼────────────────────────────────────┐
│                 │            │          Server                    │
│  ┌──────────────┴────────────┴──────────────────────────────┐    │
│  │                     FastAPI                               │    │
│  │                                                           │    │
│  │  ┌──────────┐  ┌───────────────────┐                     │    │
│  │  │ Routers  │  │ WebSocket Manager │                     │    │
│  │  └────┬─────┘  └─────────┬─────────┘                     │    │
│  │       │                  │                                │    │
│  │       └──────┬───────────┘                                │    │
│  │              │                                            │    │
│  │       ┌──────┴──────┐                                     │    │
│  │       │  Services   │  (Business logic)                   │    │
│  │       └──────┬──────┘                                     │    │
│  │              │                                            │    │
│  │       ┌──────┴──────┐                                     │    │
│  │       │Repositories │  (Data access)                      │    │
│  │       └──────┬──────┘                                     │    │
│  │              │                                            │    │
│  │       ┌──────┴──────┐                                     │    │
│  │       │ SQLAlchemy  │                                     │    │
│  │       └──────┬──────┘                                     │    │
│  └──────────────┼────────────────────────────────────────────┘    │
│                 │                                                  │
│          ┌──────┴──────┐                                          │
│          │   SQLite    │                                          │
│          └─────────────┘                                          │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. Frontend Responsibilities

| Concern               | Approach                                         |
|-----------------------|--------------------------------------------------|
| Routing               | Next.js App Router (file-based)                  |
| UI rendering          | React components with Tailwind CSS               |
| Data fetching         | TanStack Query (server state)                    |
| Global client state   | Zustand (auth token, online status)              |
| API communication     | Centralized `apiClient` abstraction              |
| Real-time events      | `wsClient` singleton with reconnection           |
| Icons                 | Lucide React                                     |

**Key principle:** Components don't call `fetch` directly. They use service functions (via TanStack Query hooks) which delegate to the API client. This keeps components focused on rendering.

---

## 3. Backend Responsibilities

| Concern              | Approach                                          |
|---------------------|---------------------------------------------------|
| HTTP API             | FastAPI routers                                   |
| Business logic       | Service layer (pure logic, no HTTP/DB knowledge)  |
| Data access          | Repository layer (SQLAlchemy queries)             |
| Validation           | Pydantic schemas (request/response DTOs)          |
| Authentication       | JWT tokens via `python-jose`                      |
| Password hashing     | bcrypt via `passlib`                              |
| Real-time            | FastAPI WebSocket with ConnectionManager          |
| Database             | SQLAlchemy 2.x async + SQLite (aiosqlite)         |
| Migrations           | Alembic                                           |

---

## 4. REST API Responsibilities

REST handles all **request-response** operations:

- **Authentication:** Register, login, OTP verification, token refresh
- **CRUD:** Users, contacts, conversations, groups
- **Queries:** Message history (paginated), search, conversation lists
- **State changes:** Create conversation, add group member, update profile

REST is idempotent, cacheable, and stateless — ideal for these operations.

---

## 5. WebSocket Responsibilities

WebSocket handles all **real-time push** events:

- **New messages:** Delivered instantly to all online conversation members
- **Typing indicators:** Ephemeral, never persisted
- **Delivery/read receipts:** Pushed as they happen
- **Presence:** Online/offline status changes

```
Client A                  Server                    Client B
   │                        │                          │
   ├── send message ──────►│                          │
   │                        ├── persist ──► DB        │
   │                        │                          │
   │                        ├── new_message ─────────►│
   │                        │                          │
   │                        │◄── message_read ────────┤
   │◄── message_read ──────┤                          │
   │                        │                          │
```

---

## 6. Database Responsibilities

SQLite (via SQLAlchemy async) handles persistence:

- User accounts and profiles
- Contact lists
- Conversation metadata and membership
- Message content and timestamps
- Delivery/read receipts

See `docs/database.md` for the complete schema design.

---

## 7. Authentication Flow

```
┌────────┐                      ┌────────┐                ┌────┐
│ Client │                      │ Server │                │ DB │
└───┬────┘                      └───┬────┘                └─┬──┘
    │                               │                       │
    │  POST /auth/register          │                       │
    │  { phone_number, password }   │                       │
    ├──────────────────────────────►│                       │
    │                               │  Insert user          │
    │                               ├──────────────────────►│
    │                               │                       │
    │  200 { message: "OTP sent" }  │                       │
    │◄──────────────────────────────┤                       │
    │                               │                       │
    │  POST /auth/verify-otp        │                       │
    │  { phone_number, otp }        │                       │
    ├──────────────────────────────►│                       │
    │                               │  Verify OTP (mocked)  │
    │                               │  Generate JWT         │
    │  200 { access_token, ... }    │                       │
    │◄──────────────────────────────┤                       │
    │                               │                       │
    │  All subsequent requests      │                       │
    │  Authorization: Bearer <JWT>  │                       │
    ├──────────────────────────────►│                       │
    │                               │  Decode & validate    │
    │                               │                       │
```

**Mock OTP:** For this assignment, OTP verification uses a fixed code (e.g. `123456`). No SMS gateway is needed.

---

## 8. Message Flow (Direct)

```
Sender                      Server                    Recipient
  │                            │                          │
  │  POST or WS: new_message   │                          │
  │  { conversation_id,        │                          │
  │    content }               │                          │
  ├───────────────────────────►│                          │
  │                            │                          │
  │                            │  1. Validate sender is   │
  │                            │     a conversation member│
  │                            │                          │
  │                            │  2. Persist message      │
  │                            │     + receipt (SENT)     │
  │                            │                          │
  │  WS: new_message           │                          │
  │◄───────────────────────────┤                          │
  │  (echo back with ID)       │                          │
  │                            │  3. Push to recipient    │
  │                            ├─────────────────────────►│
  │                            │     WS: new_message      │
  │                            │                          │
  │                            │  4. If online → DELIVERED│
  │                            │◄─────────────────────────┤
  │  WS: message_delivered     │     WS: message_delivered│
  │◄───────────────────────────┤                          │
  │                            │                          │
  │                            │  5. User reads message   │
  │                            │◄─────────────────────────┤
  │  WS: message_read          │     WS: message_read     │
  │◄───────────────────────────┤                          │
  │                            │                          │
```

---

## 9. Group Message Flow

```
Sender                      Server                Members (N)
  │                            │                       │
  │  WS: new_message           │                       │
  │  { conversation_id,        │                       │
  │    content }               │                       │
  ├───────────────────────────►│                       │
  │                            │                       │
  │                            │  1. Look up all       │
  │                            │     conversation      │
  │                            │     members           │
  │                            │                       │
  │                            │  2. Persist message   │
  │                            │     + N receipts      │
  │                            │     (one per member)  │
  │                            │                       │
  │                            │  3. Push to each      │
  │                            │     online member     │
  │                            ├──────────────────────►│ (fan-out)
  │                            │                       │
  │                            │  4. Track receipts    │
  │                            │     per member        │
  │                            │     independently     │
  │                            │                       │
```

The key difference from direct messaging: **receipts are per-member**. A message may be "read" by 3 of 5 group members. The sender sees aggregated status.

---

## 10. Important Architectural Decisions

### Layered backend (Router → Service → Repository)

**Why:** Keeps each layer testable and focused. Routers handle HTTP concerns (status codes, headers). Services contain business rules. Repositories encapsulate SQL. This is the standard pattern for interview-explainable code.

### TanStack Query for server state, Zustand for client state

**Why:** Most frontend state is "server state" (messages, contacts, conversations) — TanStack Query handles caching, refetching, and staleness automatically. Zustand is only used for truly client-side global state (auth token, user identity). This avoids the over-engineering of putting everything in a global store.

### Centralized API + WebSocket clients

**Why:** A single module manages auth headers, error handling, and base URL. No component ever calls `fetch()` directly. When the backend URL changes, one file changes.

### Async SQLAlchemy with aiosqlite

**Why:** FastAPI is async-first. Using sync SQLAlchemy would block the event loop on every query. `aiosqlite` wraps SQLite in an async interface, keeping the server responsive.

### Single `conversations` table for direct + group

**Why:** Both types share the same message schema. A `type` discriminator column is simpler than table-per-type inheritance.

### UUIDs as primary keys

**Why:** Prevents sequential ID enumeration (security), enables future client-side ID generation (offline support), and is portable across databases.

---

## 11. Future Scalability Considerations

| Concern                | Current (Phase 0)      | Future Path                              |
|------------------------|------------------------|------------------------------------------|
| Database               | SQLite (single file)   | PostgreSQL (connection pooling)          |
| WebSocket scaling      | In-memory manager      | Redis pub/sub for multi-process          |
| File storage           | Not implemented        | S3 / object storage for attachments      |
| Search                 | SQL LIKE queries       | Full-text search (SQLite FTS / Postgres) |
| Rate limiting          | Not implemented        | FastAPI middleware or reverse proxy      |
| Deployment             | Docker Compose         | Kubernetes / cloud-native                |
| Background tasks       | Not needed yet         | Celery / ARQ for notifications           |
| Caching                | TanStack Query only    | Redis for server-side caching            |

The current architecture is designed so that each of these upgrades can be made **incrementally** without rewriting the application.
