# API Reference

## Overview

The backend API follows RESTful principles for standard transactional operations (authentication, contacts, message retrieval) and uses a persistent **WebSocket** connection for real-time messaging, typing indicators, presence, and receipt tracking.

- **Base REST URL:** `http://localhost:8000`
- **WebSocket Endpoint:** `ws://localhost:8000/ws?token=<JWT_ACCESS_TOKEN>`

All REST endpoints accept and return JSON. Authenticated requests require a JWT Bearer token in the `Authorization` header:
```http
Authorization: Bearer <access_token>
```

---

## REST Endpoints

### 1. Authentication — `/auth`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register a new user with username and password. Returns `user_id` and mocked OTP (`123456`). | No |
| `POST` | `/auth/verify` | Verify OTP for phone/username registration. Returns JWT access token and user profile. | No |
| `POST` | `/auth/login` | Authenticate with username or phone and password. Returns JWT access token and user profile. | No |
| `GET` | `/auth/me` | Fetch currently authenticated user profile. | Yes |

#### Registration Payload Example:
```json
POST /auth/register
{
  "username": "alice",
  "password": "Password123!",
  "phone": "+1234567890",
  "display_name": "Alice"
}
```

#### Login Payload Example:
```json
POST /auth/login
{
  "identifier": "alice",
  "password": "Password123!"
}
```

---

### 2. Users — `/users`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/users/me` | Return the profile of the caller. | Yes |
| `GET` | `/users/{id}` | Return public user profile by UUID. | Yes |
| `PATCH` | `/users/{id}` | Update profile information (`display_name`, `avatar_url`). | Yes |
| `GET` | `/users/search?q={query}` | Search users by username or display name (excludes caller). | Yes |

---

### 3. Contacts — `/contacts`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/contacts` | Retrieve all contacts saved by the caller. | Yes |
| `POST` | `/contacts` | Add a contact by user ID (`{"contact_user_id": "<uuid>"}`). | Yes |
| `DELETE` | `/contacts/{id}` | Delete a contact relationship by contact UUID. | Yes |

---

### 4. Conversations & Messaging — `/conversations`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/conversations` | List all conversations the caller is an active member of (includes latest message preview and members). | Yes |
| `POST` | `/conversations/direct` | Get or create a 1-on-1 direct conversation (`{"other_user_id": "<uuid>"}`). | Yes |
| `POST` | `/conversations/group` | Create a group conversation (`{"name": "...", "member_ids": ["<uuid>"]}`). Creator is assigned `ADMIN` role. | Yes |
| `GET` | `/conversations/{id}` | Retrieve details of a conversation (caller must be a member). | Yes |
| `GET` | `/conversations/{id}/messages` | Get paginated messages for conversation (`limit` default 50, `offset` default 0). | Yes |
| `POST` | `/conversations/{id}/messages` | Send a new message. Persists to database and broadcasts via WebSocket. | Yes |
| `POST` | `/conversations/{id}/read` | Mark all unread messages in the conversation as `READ` for the caller. Broadcasts read receipts. | Yes |

#### Send Message Request:
```json
POST /conversations/{conversation_id}/messages
{
  "content": "Hello Bob!",
  "message_type": "TEXT"
}
```

#### Message Response Structure:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "conversation_id": "8bb988d1-7fa7-4f93-b673-90d2e8aa1b33",
  "sender_id": "cfc6c7f4-e6fb-4e4c-9ca1-b32fd6327e24",
  "content": "Hello Bob!",
  "message_type": "TEXT",
  "status": "DELIVERED",
  "created_at": "2026-10-07T16:43:20.123456Z",
  "updated_at": "2026-10-07T16:43:20.123456Z",
  "sender": {
    "id": "cfc6c7f4-e6fb-4e4c-9ca1-b32fd6327e24",
    "username": "alice",
    "display_name": "Alice",
    "avatar_url": null
  },
  "receipts": [
    {
      "id": "d1e7c9b8-...",
      "message_id": "3fa85f64-...",
      "user_id": "d93872a8-...",
      "status": "DELIVERED",
      "timestamp": "2026-10-07T16:43:20.125000Z"
    }
  ]
}
```

---

### 5. Health — `/health`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/health` | Check service health and database connectivity. | No |

---

## WebSocket Events

The WebSocket connection is established at:
```
ws://localhost:8000/ws?token=<JWT_ACCESS_TOKEN>
```

### Event Format:
```json
{
  "type": "<EVENT_TYPE>",
  "payload": { ... }
}
```

### Supported Event Types:

| Event Type | Direction | Payload | Description |
|---|---|---|---|
| `ping` | Client → Server | `{}` | Heartbeat ping from client every 25s. |
| `pong` | Server → Client | `{}` | Heartbeat pong acknowledging connection is alive. |
| `typing.started` | Bidirectional | `{"conversation_id": "<uuid>", "user_id": "<uuid>"}` | Dispatched when a member starts typing. |
| `typing.stopped` | Bidirectional | `{"conversation_id": "<uuid>", "user_id": "<uuid>"}` | Dispatched when typing stops or message sends. |
| `message.created` | Server → Client | Full `MessageResponse` object | Dispatched to active conversation members when a message is sent. |
| `message.delivered`| Server → Client | `{"conversation_id": "<uuid>", "message_id": "<uuid>", "user_id": "<uuid>"}` | Dispatched when an offline recipient comes online and messages are delivered. |
| `message.read` | Bidirectional | `{"conversation_id": "<uuid>", "message_ids": ["<uuid>"], "user_id": "<uuid>"}` | Dispatched when a recipient marks messages as read. |
| `presence.updated`| Server → Client | `{"user_id": "<uuid>", "is_online": boolean, "last_seen": string}` | Dispatched to users when a user connects or disconnects. |
