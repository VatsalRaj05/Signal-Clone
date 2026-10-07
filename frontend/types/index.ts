/**
 * Shared TypeScript types for the application.
 *
 * These mirror the backend Pydantic schemas and database models.
 * Defined once here so every component/service uses the same shape.
 */

// ── Users ──────────────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  phone: string | null;
  display_name: string | null;
  avatar_url: string | null;
  is_online: boolean;
  last_seen: string | null;
  created_at: string;
  updated_at: string;
}

/** Minimal user profile embedded in contacts / messages / members */
export interface ContactUser {
  id: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
  is_online: boolean;
  last_seen: string | null;
}

// ── Auth ───────────────────────────────────────────────────────────

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface LoginResponse extends AuthTokens {
  user: User;
}

export interface LoginRequest {
  identifier: string;
  password?: string;
}

export interface VerifyOTPRequest {
  identifier: string;
  otp: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  phone?: string;
  display_name?: string;
}

// ── Contacts ───────────────────────────────────────────────────────

export interface Contact {
  id: string;
  user_id: string;
  contact_user_id: string;
  contact_user: ContactUser;
  created_at: string;
}

export interface AddContactRequest {
  contact_user_id: string;
}

// ── Conversations ──────────────────────────────────────────────────

/** Backend uses uppercase enum values (DIRECT, GROUP) */
export type ConversationType = "DIRECT" | "GROUP";

export interface ConversationMember {
  id: string;
  conversation_id: string;
  user_id: string;
  role: "ADMIN" | "MEMBER";
  joined_at: string;
  user: ContactUser;
}

export interface LatestMessage {
  id: string;
  sender_id: string | null;
  content: string;
  status?: "SENT" | "DELIVERED" | "READ";
  created_at: string;
}

export interface Conversation {
  id: string;
  type: ConversationType;
  name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
  members: ConversationMember[];
  latest_message: LatestMessage | null;
}

// ── Messages ───────────────────────────────────────────────────────

export type MessageType = "TEXT" | "IMAGE" | "FILE" | "SYSTEM";

export interface MessageSender {
  id: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string | null;
  content: string;
  message_type: MessageType;
  status?: "SENT" | "DELIVERED" | "READ";
  created_at: string;
  updated_at: string;
  sender: MessageSender | null;
  receipts?: MessageReceipt[];
}

export interface MessageReceipt {
  id: string;
  message_id: string;
  user_id: string;
  status: "SENT" | "DELIVERED" | "READ";
  timestamp: string;
}

// ── WebSocket Events ───────────────────────────────────────────────

export type WSEventType =
  | "new_message"
  | "typing"
  | "message_delivered"
  | "message_read"
  | "user_online"
  | "user_offline"
  | "message.created"
  | "message.delivered"
  | "message.read"
  | "typing.started"
  | "typing.stopped"
  | "presence.updated"
  | "pong";

export interface WSEvent<T = unknown> {
  type: WSEventType;
  payload: T;
}

// ── API ────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
