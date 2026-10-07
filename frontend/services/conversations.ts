/**
 * Conversation and message service — wraps conversation-related API calls.
 */

import { apiClient } from "@/lib/api-client";
import type { Conversation, Message } from "@/types";

export const conversationService = {
  list: () => apiClient.get<Conversation[]>("/conversations"),

  getOrCreateDirect: (otherUserId: string) =>
    apiClient.post<Conversation>("/conversations/direct", {
      other_user_id: otherUserId,
    }),

  createGroup: (name: string, memberIds: string[]) =>
    apiClient.post<Conversation>("/conversations/group", {
      name,
      member_ids: memberIds,
    }),

  get: (conversationId: string) =>
    apiClient.get<Conversation>(`/conversations/${conversationId}`),

  getMessages: (conversationId: string, limit = 50, offset = 0) =>
    apiClient.get<Message[]>(
      `/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`
    ),

  sendMessage: (conversationId: string, content: string, messageType: string = "TEXT") =>
    apiClient.post<Message>(`/conversations/${conversationId}/messages`, {
      content,
      message_type: messageType,
    }),

  markRead: (conversationId: string) =>
    apiClient.post<{ status: string; read_count: number; message_ids: string[] }>(
      `/conversations/${conversationId}/read`
    ),
};

