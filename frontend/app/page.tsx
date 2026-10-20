"use client";

import React, { useEffect, useState, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Plus,
  LogOut,
  MessageCircle,
  X,
  ChevronLeft,
  Loader2,
  UserPlus,
  Check,
  CheckCheck,
  Shield,
  Users,
  Send,
  MoreVertical,
  Edit3,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { conversationService } from "@/services/conversations";
import { contactsService } from "@/services/contacts";
import { authService } from "@/services/auth";
import { wsClient } from "@/lib/ws-client";
import type { Conversation, Message, ContactUser } from "@/types";

// ── Helpers ──────────────────────────────────────────────────────────────────

function getDisplayName(conv: Conversation, myUserId: string): string {
  if (conv.type === "GROUP") return conv.name ?? "Group";
  const other = conv.members.find((m) => m.user_id !== myUserId);
  return other?.user.display_name ?? other?.user.username ?? "Unknown";
}

function getOtherMember(conv: Conversation, myUserId: string) {
  if (conv.type === "GROUP") return null;
  return conv.members.find((m) => m.user_id !== myUserId)?.user ?? null;
}

function getAvatarInitial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "?";
}

function formatMessageTime(iso: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatSidebarDate(iso: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } else if (diffDays === 1) {
    return "Yesterday";
  } else if (diffDays < 7) {
    return date.toLocaleDateString([], { weekday: "short" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function formatLastSeen(isOnline: boolean, lastSeenIso?: string | null): string {
  if (isOnline) return "Online";
  if (!lastSeenIso) return "Offline";
  const date = new Date(lastSeenIso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 2) return "Last seen just now";
  if (diffMins < 60) return `Last seen ${diffMins}m ago`;
  if (diffDays === 0) {
    return `Last seen today at ${date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
  }
  if (diffDays === 1) {
    return `Last seen yesterday at ${date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
  }
  return `Last seen ${date.toLocaleDateString([], { month: "short", day: "numeric" })}`;
}

function getMessageDateDivider(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return date.toLocaleDateString([], { month: "long", day: "numeric", year: "numeric" });
}

const AVATAR_COLORS = [
  "bg-[#2c6bed]", // Signal blue
  "bg-emerald-600",
  "bg-amber-600",
  "bg-rose-600",
  "bg-purple-600",
  "bg-teal-600",
  "bg-indigo-600",
  "bg-cyan-600",
];

function avatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

// ── Avatar Component ─────────────────────────────────────────────────────────

function Avatar({
  name,
  size = "md",
  avatarUrl,
  isOnline = false,
  showBadge = false,
}: {
  name: string;
  size?: "xs" | "sm" | "md" | "lg";
  avatarUrl?: string | null;
  isOnline?: boolean;
  showBadge?: boolean;
}) {
  const sizeClasses = {
    xs: "w-6 h-6 text-[10px]",
    sm: "w-8 h-8 text-xs",
    md: "w-10 h-10 text-sm",
    lg: "w-12 h-12 text-base",
  }[size];

  return (
    <div className="relative flex-shrink-0">
      {avatarUrl ? (
        <img
          src={avatarUrl}
          alt={name}
          className={`${sizeClasses} rounded-full object-cover`}
        />
      ) : (
        <div
          className={`${sizeClasses} ${avatarColor(name)} rounded-full flex items-center justify-center font-medium text-white select-none`}
        >
          {getAvatarInitial(name)}
        </div>
      )}
      {showBadge && isOnline && (
        <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full ring-2 ring-[#1b1c20]" />
      )}
    </div>
  );
}

// ── Receipt Status Icon ──────────────────────────────────────────────────────

function ReceiptStatusIcon({
  status,
  className = "w-3.5 h-3.5",
}: {
  status?: string;
  className?: string;
}) {
  if (status === "READ") {
    return <CheckCheck className={`${className} text-sky-400`} />;
  }
  if (status === "DELIVERED") {
    return <CheckCheck className={`${className} text-zinc-400`} />;
  }
  return <Check className={`${className} text-zinc-400`} />;
}

// ── Modals ───────────────────────────────────────────────────────────────────

function AddContactModal({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(t);
  }, [query]);

  const { data: results = [], isLoading } = useQuery({
    queryKey: ["userSearch", debouncedQuery],
    queryFn: () => contactsService.search(debouncedQuery),
    enabled: debouncedQuery.trim().length > 0,
  });

  const addMutation = useMutation({
    mutationFn: (userId: string) =>
      contactsService.add({ contact_user_id: userId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-[#1f2126] border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-white font-semibold text-base">Add Contact</h2>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 border-b border-zinc-800">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by username or name…"
              className="w-full bg-[#16171b] text-white placeholder-zinc-500 rounded-xl pl-10 pr-4 py-2 text-sm outline-none focus:ring-1 focus:ring-[#2c6bed] transition border border-zinc-800"
            />
          </div>
        </div>

        <div className="max-h-72 overflow-y-auto px-2 py-3 space-y-1">
          {isLoading && (
            <div className="flex justify-center py-6">
              <Loader2 className="w-5 h-5 animate-spin text-[#2c6bed]" />
            </div>
          )}

          {!isLoading && debouncedQuery && results.length === 0 && (
            <p className="text-center text-zinc-500 text-sm py-6">No users found</p>
          )}

          {!debouncedQuery && (
            <p className="text-center text-zinc-500 text-xs py-6">
              Type a username to find people
            </p>
          )}

          {results.map((user: ContactUser) => (
            <div
              key={user.id}
              className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-zinc-800/60 transition"
            >
              <Avatar name={user.display_name ?? user.username} avatarUrl={user.avatar_url} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">
                  {user.display_name ?? user.username}
                </p>
                <p className="text-zinc-500 text-xs truncate">@{user.username}</p>
              </div>
              <button
                onClick={() => addMutation.mutate(user.id)}
                disabled={addMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#2c6bed] hover:bg-[#3d79f2] disabled:opacity-50 rounded-lg text-white text-xs font-medium transition"
              >
                <UserPlus className="w-3.5 h-3.5" />
                Add
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function NewConversationModal({
  onClose,
  onConversationCreated,
}: {
  onClose: () => void;
  onConversationCreated: (convId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 250);
    return () => clearTimeout(t);
  }, [query]);

  // Load contacts for quick selection
  const { data: contacts = [] } = useQuery({
    queryKey: ["contacts"],
    queryFn: contactsService.list,
  });

  // Search results
  const { data: searchResults = [], isLoading: searchLoading } = useQuery({
    queryKey: ["userSearchNew", debouncedQuery],
    queryFn: () => contactsService.search(debouncedQuery),
    enabled: debouncedQuery.trim().length > 0,
  });

  const createMutation = useMutation({
    mutationFn: (userId: string) => conversationService.getOrCreateDirect(userId),
    onSuccess: (conv) => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      onConversationCreated(conv.id);
      onClose();
    },
  });

  const displayList = debouncedQuery.trim().length > 0
    ? searchResults
    : contacts.map((c) => c.contact_user);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-[#1f2126] border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-white font-semibold text-base">New Chat</h2>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 border-b border-zinc-800">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search people to message…"
              className="w-full bg-[#16171b] text-white placeholder-zinc-500 rounded-xl pl-10 pr-4 py-2 text-sm outline-none focus:ring-1 focus:ring-[#2c6bed] transition border border-zinc-800"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
          {searchLoading && (
            <div className="flex justify-center py-6">
              <Loader2 className="w-5 h-5 animate-spin text-[#2c6bed]" />
            </div>
          )}

          {!searchLoading && displayList.length === 0 && (
            <p className="text-center text-zinc-500 text-xs py-8">
              {debouncedQuery ? "No users found" : "No contacts yet. Type a username above."}
            </p>
          )}

          {displayList.map((user: ContactUser) => (
            <button
              key={user.id}
              onClick={() => createMutation.mutate(user.id)}
              disabled={createMutation.isPending}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-zinc-800/60 transition text-left disabled:opacity-50"
            >
              <Avatar
                name={user.display_name ?? user.username}
                avatarUrl={user.avatar_url}
                size="md"
                isOnline={user.is_online}
                showBadge
              />
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">
                  {user.display_name ?? user.username}
                </p>
                <p className="text-zinc-500 text-xs truncate">@{user.username}</p>
              </div>
              {createMutation.isPending && (
                <Loader2 className="w-4 h-4 animate-spin text-[#2c6bed]" />
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function NewGroupModal({
  onClose,
  onGroupCreated,
}: {
  onClose: () => void;
  onGroupCreated: (convId: string) => void;
}) {
  const [name, setName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedUsers, setSelectedUsers] = useState<ContactUser[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const qc = useQueryClient();

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(searchQuery), 250);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const { data: contacts = [] } = useQuery({
    queryKey: ["contacts"],
    queryFn: contactsService.list,
  });

  const { data: searchResults = [], isLoading: searchLoading } = useQuery({
    queryKey: ["groupUserSearch", debouncedQuery],
    queryFn: () => contactsService.search(debouncedQuery),
    enabled: debouncedQuery.trim().length > 0,
  });

  const displayList: ContactUser[] = debouncedQuery.trim().length > 0
    ? searchResults
    : contacts.map((c) => c.contact_user);

  const createMutation = useMutation({
    mutationFn: () =>
      conversationService.createGroup(
        name.trim(),
        selectedUsers.map((u) => u.id)
      ),
    onSuccess: (conv) => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      onGroupCreated(conv.id);
      onClose();
    },
    onError: (err: any) => {
      setErrorMsg(err?.message || "Failed to create group. Please try again.");
    },
  });

  const toggleUser = (user: ContactUser) => {
    setSelectedUsers((prev) =>
      prev.some((u) => u.id === user.id)
        ? prev.filter((u) => u.id !== user.id)
        : [...prev, user]
    );
  };

  const removeUser = (userId: string) => {
    setSelectedUsers((prev) => prev.filter((u) => u.id !== userId));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-[#1f2126] border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-white font-semibold text-base">New Group</h2>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMsg && (
          <div className="mx-4 mt-3 p-2.5 rounded-lg bg-red-900/50 border border-red-500/50 text-red-200 text-xs">
            {errorMsg}
          </div>
        )}

        <div className="p-4 border-b border-zinc-800 space-y-3">
          <input
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (errorMsg) setErrorMsg("");
            }}
            placeholder="Group Name *"
            className="w-full bg-[#16171b] text-white placeholder-zinc-500 rounded-xl px-4 py-2 text-sm outline-none focus:ring-1 focus:ring-[#2c6bed] transition border border-zinc-800"
          />

          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search people to add…"
              className="w-full bg-[#16171b] text-white placeholder-zinc-500 rounded-xl pl-10 pr-4 py-2 text-sm outline-none focus:ring-1 focus:ring-[#2c6bed] transition border border-zinc-800"
            />
          </div>
        </div>

        {selectedUsers.length > 0 && (
          <div className="px-4 py-2 border-b border-zinc-800/60 flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {selectedUsers.map((u) => (
              <span
                key={u.id}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#2c6bed]/20 text-[#6ba1ff] text-xs font-medium border border-[#2c6bed]/30"
              >
                <span>{u.display_name ?? u.username}</span>
                <button
                  type="button"
                  onClick={() => removeUser(u.id)}
                  className="hover:text-white transition"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="px-4 py-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider flex justify-between">
          <span>{debouncedQuery.trim() ? "Search Results" : "Contacts"}</span>
          <span>{selectedUsers.length} selected</span>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1 min-h-[160px]">
          {searchLoading && (
            <div className="flex justify-center py-6">
              <Loader2 className="w-5 h-5 animate-spin text-[#2c6bed]" />
            </div>
          )}

          {!searchLoading && displayList.length === 0 && (
            <div className="text-center text-zinc-500 text-xs py-8 px-4">
              {debouncedQuery.trim()
                ? "No users found matching that username."
                : "No contacts yet. Type a username in the search box above to find members."}
            </div>
          )}

          {!searchLoading &&
            displayList.map((user) => {
              const isSelected = selectedUsers.some((u) => u.id === user.id);
              return (
                <button
                  key={user.id}
                  onClick={() => toggleUser(user)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl transition text-left ${
                    isSelected ? "bg-[#2c6bed]/20 text-white" : "hover:bg-zinc-800/60"
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded-md border flex items-center justify-center transition ${
                      isSelected
                        ? "bg-[#2c6bed] border-[#2c6bed] text-white"
                        : "border-zinc-700 bg-zinc-800"
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5" />}
                  </div>
                  <Avatar
                    name={user.display_name ?? user.username}
                    avatarUrl={user.avatar_url}
                    size="sm"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-medium truncate">
                      {user.display_name ?? user.username}
                    </p>
                    <p className="text-zinc-500 text-xs truncate">@{user.username}</p>
                  </div>
                </button>
              );
            })}
        </div>

        <div className="p-4 border-t border-zinc-800">
          <button
            onClick={() => createMutation.mutate()}
            disabled={!name.trim() || createMutation.isPending}
            className="w-full py-2.5 bg-[#2c6bed] hover:bg-[#3d79f2] disabled:opacity-50 text-white font-medium text-sm rounded-xl transition flex items-center justify-center gap-2"
          >
            {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            {selectedUsers.length > 0
              ? `Create Group (${selectedUsers.length + 1} members)`
              : "Create Group"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Conversation Sidebar Item ─────────────────────────────────────────────────

function ConversationItem({
  conv,
  myUserId,
  isActive,
  isTyping,
  onClick,
}: {
  conv: Conversation;
  myUserId: string;
  isActive: boolean;
  isTyping: boolean;
  onClick: () => void;
}) {
  const name = getDisplayName(conv, myUserId);
  const other = getOtherMember(conv, myUserId);
  const latest = conv.latest_message;
  const isMine = latest?.sender_id === myUserId;
  const timestamp = latest?.created_at ? formatSidebarDate(latest.created_at) : "";

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition text-left ${
        isActive
          ? "bg-zinc-800/80 shadow-xs border border-zinc-700/40"
          : "hover:bg-zinc-800/40 border border-transparent"
      }`}
    >
      <Avatar
        name={name}
        size="md"
        avatarUrl={conv.type === "GROUP" ? conv.avatar_url : other?.avatar_url}
        isOnline={conv.type === "DIRECT" ? other?.is_online : false}
        showBadge={conv.type === "DIRECT"}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1">
          <span className="text-white text-sm font-semibold truncate">{name}</span>
          {timestamp && (
            <span className="text-zinc-500 text-[11px] flex-shrink-0">{timestamp}</span>
          )}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          {isTyping ? (
            <span className="text-[#2c6bed] text-xs font-medium italic animate-pulse">
              typing…
            </span>
          ) : latest ? (
            <div className="flex items-center gap-1 text-zinc-400 text-xs truncate">
              {isMine && (
                <ReceiptStatusIcon
                  status={latest.status}
                  className="w-3.5 h-3.5 flex-shrink-0"
                />
              )}
              <span className="truncate">{latest.content}</span>
            </div>
          ) : (
            <span className="text-zinc-500 text-xs italic">No messages yet</span>
          )}
        </div>
      </div>
    </button>
  );
}

// ── Message Bubble ───────────────────────────────────────────────────────────

function MessageBubble({
  msg,
  isMine,
  showSenderName,
}: {
  msg: Message;
  isMine: boolean;
  showSenderName: boolean;
}) {
  const time = formatMessageTime(msg.created_at);
  const senderName = msg.sender?.display_name ?? msg.sender?.username ?? "";

  return (
    <div
      className={`flex flex-col ${
        isMine ? "items-end" : "items-start"
      } w-full group select-text`}
    >
      {/* Sender name for received group messages */}
      {!isMine && showSenderName && senderName && (
        <span className="text-[11px] font-medium text-zinc-400 mb-1 px-1">
          {senderName}
        </span>
      )}

      {/* Bubble container */}
      <div
        className={`relative max-w-[80%] sm:max-w-[70%] px-3.5 py-2 rounded-2xl text-[14.5px] leading-relaxed break-words shadow-xs ${
          isMine
            ? "bg-[#2c6bed] text-white rounded-br-xs"
            : "bg-[#282a2f] text-zinc-100 rounded-bl-xs"
        }`}
      >
        <span>{msg.content}</span>

        {/* Timestamp & Status ticks inline */}
        <div
          className={`inline-flex items-center gap-1 float-right mt-1 ml-2 text-[11px] select-none ${
            isMine ? "text-blue-100/80" : "text-zinc-400"
          }`}
        >
          <span>{time}</span>
          {isMine && <ReceiptStatusIcon status={msg.status} className="w-3.5 h-3.5" />}
        </div>
      </div>
    </div>
  );
}

// ── Chat Area ────────────────────────────────────────────────────────────────

function ChatArea({
  conv,
  myUserId,
  onBack,
}: {
  conv: Conversation;
  myUserId: string;
  onBack: () => void;
}) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [inputText, setInputText] = useState("");
  const qc = useQueryClient();
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const typingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isTypingEmittedRef = useRef(false);

  const name = getDisplayName(conv, myUserId);
  const otherMember = getOtherMember(conv, myUserId);

  // Messages Query
  const { data: messages = [], isLoading, isError } = useQuery({
    queryKey: ["messages", conv.id],
    queryFn: () => conversationService.getMessages(conv.id),
  });

  // Automatically mark read when messages load or active conversation opens
  useEffect(() => {
    if (conv.id) {
      conversationService.markRead(conv.id).catch(() => {});
      wsClient.send({
        type: "message.read",
        payload: { conversation_id: conv.id },
      });
    }
  }, [conv.id, messages.length]);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typingUsers]);

  // WebSocket listeners for this chat
  useEffect(() => {
    const unsubCreated = wsClient.on<Message>("message.created", (payload) => {
      if (payload.conversation_id === conv.id) {
        qc.setQueryData<Message[]>(["messages", conv.id], (old = []) => {
          if (old.some((m) => m.id === payload.id)) return old;
          return [...old, payload];
        });
        setTypingUsers((prev) => prev.filter((id) => id !== payload.sender_id));

        // If recipient received a message while currently in this chat, mark read immediately
        if (payload.sender_id !== myUserId) {
          conversationService.markRead(conv.id).catch(() => {});
          wsClient.send({
            type: "message.read",
            payload: { conversation_id: conv.id, message_ids: [payload.id] },
          });
        }
      }
      qc.invalidateQueries({ queryKey: ["conversations"] });
    });

    const unsubRead = wsClient.on<{ conversation_id: string; message_ids?: string[] }>(
      "message.read",
      (payload) => {
        if (payload.conversation_id === conv.id) {
          qc.setQueryData<Message[]>(["messages", conv.id], (old = []) =>
            old.map((m) => {
              if (!payload.message_ids || payload.message_ids.includes(m.id)) {
                return { ...m, status: "READ" };
              }
              return m;
            })
          );
          qc.invalidateQueries({ queryKey: ["conversations"] });
        }
      }
    );

    const unsubDelivered = wsClient.on<{ conversation_id: string; message_id?: string }>(
      "message.delivered",
      (payload) => {
        if (payload.conversation_id === conv.id) {
          qc.setQueryData<Message[]>(["messages", conv.id], (old = []) =>
            old.map((m) => {
              if (m.id === payload.message_id && m.status !== "READ") {
                return { ...m, status: "DELIVERED" };
              }
              return m;
            })
          );
          qc.invalidateQueries({ queryKey: ["conversations"] });
        }
      }
    );

    const unsubTypingStarted = wsClient.on<{ conversation_id: string; user_id: string }>(
      "typing.started",
      (payload) => {
        if (payload.conversation_id === conv.id && payload.user_id !== myUserId) {
          setTypingUsers((prev) => (prev.includes(payload.user_id) ? prev : [...prev, payload.user_id]));
        }
      }
    );

    const unsubTypingStopped = wsClient.on<{ conversation_id: string; user_id: string }>(
      "typing.stopped",
      (payload) => {
        if (payload.conversation_id === conv.id) {
          setTypingUsers((prev) => prev.filter((id) => id !== payload.user_id));
        }
      }
    );

    return () => {
      unsubCreated();
      unsubRead();
      unsubDelivered();
      unsubTypingStarted();
      unsubTypingStopped();
    };
  }, [conv.id, qc, myUserId]);

  // Throttled typing input handler
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputText(e.target.value);

    if (!isTypingEmittedRef.current) {
      isTypingEmittedRef.current = true;
      wsClient.send({
        type: "typing.started",
        payload: { conversation_id: conv.id },
      });
    }

    if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
    typingTimerRef.current = setTimeout(() => {
      isTypingEmittedRef.current = false;
      wsClient.send({
        type: "typing.stopped",
        payload: { conversation_id: conv.id },
      });
    }, 2500);
  };

  // Send Message Mutation
  const sendMutation = useMutation({
    mutationFn: () => conversationService.sendMessage(conv.id, inputText.trim()),
    onSuccess: (newMsg) => {
      setInputText("");
      isTypingEmittedRef.current = false;
      if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
      wsClient.send({
        type: "typing.stopped",
        payload: { conversation_id: conv.id },
      });
      qc.setQueryData<Message[]>(["messages", conv.id], (old = []) => [...old, newMsg]);
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (inputText.trim() && !sendMutation.isPending) {
        sendMutation.mutate();
      }
    }
  };

  // Subtitle header text (presence or typing)
  const headerSubtitle = useMemo(() => {
    if (typingUsers.length > 0) {
      return "typing…";
    }
    if (conv.type === "GROUP") {
      return `${conv.members.length} members`;
    }
    return formatLastSeen(otherMember?.is_online ?? false, otherMember?.last_seen);
  }, [typingUsers, conv.type, conv.members.length, otherMember?.is_online, otherMember?.last_seen]);

  // Group messages by date
  const renderedItems = useMemo(() => {
    const items: Array<{ type: "divider" | "message"; date?: string; msg?: Message }> = [];
    let lastDate = "";
    messages.forEach((msg) => {
      const dateStr = getMessageDateDivider(msg.created_at);
      if (dateStr !== lastDate) {
        items.push({ type: "divider", date: dateStr });
        lastDate = dateStr;
      }
      items.push({ type: "message", msg });
    });
    return items;
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-[#111215]">
      {/* ── Chat Header ── */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-zinc-800 bg-[#18191d] flex-shrink-0 z-10">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="sm:hidden text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-800 transition -ml-1"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <Avatar
            name={name}
            size="md"
            avatarUrl={conv.type === "GROUP" ? conv.avatar_url : otherMember?.avatar_url}
            isOnline={conv.type === "DIRECT" ? otherMember?.is_online : false}
            showBadge={conv.type === "DIRECT"}
          />
          <div className="flex flex-col min-w-0">
            <span className="text-white text-sm font-semibold truncate leading-tight">
              {name}
            </span>
            <span
              className={`text-xs truncate leading-tight ${
                typingUsers.length > 0
                  ? "text-[#2c6bed] font-medium italic animate-pulse"
                  : otherMember?.is_online
                  ? "text-emerald-400 font-medium"
                  : "text-zinc-400"
              }`}
            >
              {headerSubtitle}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 text-zinc-400">
          <button
            title="Options"
            className="p-1.5 rounded-lg hover:text-white hover:bg-zinc-800 transition"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Messages Feed ── */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5">
        {isLoading && (
          <div className="flex justify-center items-center h-full">
            <Loader2 className="w-6 h-6 animate-spin text-[#2c6bed]" />
          </div>
        )}

        {isError && (
          <div className="flex justify-center items-center h-full text-red-400 text-sm">
            Failed to load messages
          </div>
        )}

        {!isLoading && !isError && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-14 h-14 bg-zinc-800/80 rounded-full flex items-center justify-center mb-3">
              <MessageCircle className="w-6 h-6 text-zinc-500" />
            </div>
            <p className="text-white text-sm font-medium">No messages yet</p>
            <p className="text-zinc-500 text-xs mt-1">
              Send a message to start chatting!
            </p>
          </div>
        )}

        {renderedItems.map((item, idx) => {
          if (item.type === "divider") {
            return (
              <div key={`divider-${item.date}-${idx}`} className="flex justify-center my-3">
                <span className="bg-[#1e2025] border border-zinc-800 text-zinc-400 text-[11px] font-medium px-3 py-1 rounded-full shadow-xs">
                  {item.date}
                </span>
              </div>
            );
          }
          if (item.msg) {
            return (
              <MessageBubble
                key={item.msg.id}
                msg={item.msg}
                isMine={item.msg.sender_id === myUserId}
                showSenderName={conv.type === "GROUP"}
              />
            );
          }
          return null;
        })}

        {/* Typing indicator bubble */}
        {typingUsers.length > 0 && (
          <div className="flex items-center gap-2 mt-2">
            <div className="bg-[#282a2f] text-zinc-300 px-3.5 py-2 rounded-2xl rounded-bl-xs flex items-center gap-1.5 shadow-xs">
              <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Composer Bar ── */}
      <div className="p-3 bg-[#18191d] border-t border-zinc-800 flex-shrink-0">
        <div className="flex items-center gap-2 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <input
              value={inputText}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Signal message"
              disabled={sendMutation.isPending}
              className="w-full bg-[#24262c] text-white placeholder-zinc-500 text-sm rounded-full pl-4 pr-10 py-2.5 outline-none focus:ring-1 focus:ring-[#2c6bed] border border-zinc-700/50 transition"
            />
            {sendMutation.isPending && (
              <Loader2 className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-[#2c6bed]" />
            )}
          </div>

          <button
            onClick={() => {
              if (inputText.trim() && !sendMutation.isPending) {
                sendMutation.mutate();
              }
            }}
            disabled={!inputText.trim() || sendMutation.isPending}
            className="w-10 h-10 rounded-full bg-[#2c6bed] hover:bg-[#3d79f2] disabled:opacity-40 disabled:hover:bg-[#2c6bed] text-white flex items-center justify-center transition flex-shrink-0 shadow-xs"
            title="Send"
          >
            <Send className="w-4 h-4 ml-0.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Empty State ──────────────────────────────────────────────────────────────

function EmptyState({ onNewChat }: { onNewChat: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 bg-[#111215]">
      <div className="w-16 h-16 bg-[#2c6bed]/10 rounded-full flex items-center justify-center mb-4 ring-1 ring-[#2c6bed]/20">
        <Shield className="w-8 h-8 text-[#2c6bed]" />
      </div>
      <h2 className="text-white text-lg font-bold">Signal Clone</h2>
      <p className="text-zinc-400 text-xs max-w-xs mt-1.5 leading-relaxed">
        Fast, private messaging with real-time delivery and read receipts.
      </p>
      <button
        onClick={onNewChat}
        className="mt-5 flex items-center gap-2 px-4 py-2 bg-[#2c6bed] hover:bg-[#3d79f2] text-white text-xs font-semibold rounded-xl transition shadow-xs"
      >
        <Edit3 className="w-4 h-4" />
        New Message
      </button>
    </div>
  );
}

// ── Main Home Page ───────────────────────────────────────────────────────────

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, user, clearAuth, hydrateFromStorage } = useAuthStore();
  const [mounted, setMounted] = useState(false);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [sidebarSearch, setSidebarSearch] = useState("");
  const [showAddContact, setShowAddContact] = useState(false);
  const [showNewConv, setShowNewConv] = useState(false);
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [typingMap, setTypingMap] = useState<Record<string, boolean>>({});

  const qc = useQueryClient();

  // Hydrate auth
  useEffect(() => {
    hydrateFromStorage();
    setMounted(true);
  }, [hydrateFromStorage]);

  // Auth redirect
  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.push("/login");
    }
  }, [mounted, isAuthenticated, router]);

  // Fetch current user
  const { data: meData } = useQuery({
    queryKey: ["me"],
    queryFn: authService.me,
    enabled: isAuthenticated,
  });

  const currentUser = meData ?? user;
  const myId = currentUser?.id ?? "";
  const myName = currentUser?.display_name ?? currentUser?.username ?? "Me";

  // Conversations list
  const { data: conversations = [], isLoading: convsLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: conversationService.list,
    enabled: isAuthenticated,
  });

  // Global WebSocket listener
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (isAuthenticated && token) {
      wsClient.connect(token);

      const unsubCreated = wsClient.on("message.created", () => {
        qc.invalidateQueries({ queryKey: ["conversations"] });
      });

      const unsubRead = wsClient.on("message.read", () => {
        qc.invalidateQueries({ queryKey: ["conversations"] });
      });

      const unsubDelivered = wsClient.on("message.delivered", () => {
        qc.invalidateQueries({ queryKey: ["conversations"] });
      });

      const unsubPresence = wsClient.on<{ user_id: string; is_online: boolean; last_seen?: string }>(
        "presence.updated",
        (payload) => {
          qc.setQueryData<Conversation[]>(["conversations"], (old = []) =>
            old.map((c) => ({
              ...c,
              members: c.members.map((m) =>
                m.user_id === payload.user_id
                  ? {
                      ...m,
                      user: {
                        ...m.user,
                        is_online: payload.is_online,
                        last_seen: payload.last_seen ?? m.user.last_seen,
                      },
                    }
                  : m
              ),
            }))
          );
        }
      );

      const unsubTypingStart = wsClient.on<{ conversation_id: string; user_id: string }>(
        "typing.started",
        (payload) => {
          if (payload.user_id !== myId) {
            setTypingMap((prev) => ({ ...prev, [payload.conversation_id]: true }));
          }
        }
      );

      const unsubTypingStop = wsClient.on<{ conversation_id: string; user_id: string }>(
        "typing.stopped",
        (payload) => {
          setTypingMap((prev) => ({ ...prev, [payload.conversation_id]: false }));
        }
      );

      return () => {
        unsubCreated();
        unsubRead();
        unsubDelivered();
        unsubPresence();
        unsubTypingStart();
        unsubTypingStop();
      };
    }
  }, [isAuthenticated, qc, myId]);

  const activeConv = conversations.find((c) => c.id === activeConvId) ?? null;

  // Filter conversations
  const filteredConvs = conversations.filter((conv) => {
    if (!sidebarSearch.trim()) return true;
    const name = getDisplayName(conv, myId).toLowerCase();
    return name.includes(sidebarSearch.toLowerCase());
  });

  const handleLogout = () => {
    clearAuth();
    wsClient.disconnect();
    router.push("/login");
  };

  if (!mounted || !isAuthenticated) return null;

  return (
    <>
      {showAddContact && <AddContactModal onClose={() => setShowAddContact(false)} />}
      {showNewConv && (
        <NewConversationModal
          onClose={() => setShowNewConv(false)}
          onConversationCreated={(id) => setActiveConvId(id)}
        />
      )}
      {showNewGroup && (
        <NewGroupModal
          onClose={() => setShowNewGroup(false)}
          onGroupCreated={(id) => setActiveConvId(id)}
        />
      )}

      {/* Main Container */}
      <div className="flex h-screen w-screen overflow-hidden bg-[#111215] select-none text-zinc-100">
        {/* ── SIDEBAR ── */}
        <aside
          className={`flex flex-col w-full sm:w-[320px] md:w-[360px] flex-shrink-0 bg-[#1b1c20] border-r border-zinc-800/80 ${
            activeConv ? "hidden sm:flex" : "flex"
          }`}
        >
          {/* Top user profile bar */}
          <div className="h-14 px-4 flex items-center justify-between border-b border-zinc-800/80 flex-shrink-0">
            <div className="flex items-center gap-2.5 min-w-0">
              <Avatar
                name={myName}
                size="md"
                avatarUrl={currentUser?.avatar_url}
                isOnline={true}
                showBadge
              />
              <div className="flex flex-col min-w-0">
                <span className="text-white text-sm font-semibold truncate leading-tight">
                  {myName}
                </span>
                <span className="text-zinc-500 text-xs truncate leading-tight">
                  @{currentUser?.username}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-0.5 text-zinc-400">
              <button
                onClick={() => setShowNewConv(true)}
                title="New Chat"
                className="p-1.5 rounded-lg hover:text-white hover:bg-zinc-800 transition"
              >
                <Edit3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowNewGroup(true)}
                title="New Group"
                className="p-1.5 rounded-lg hover:text-white hover:bg-zinc-800 transition"
              >
                <Users className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowAddContact(true)}
                title="Add Contact"
                className="p-1.5 rounded-lg hover:text-white hover:bg-zinc-800 transition"
              >
                <UserPlus className="w-4 h-4" />
              </button>
              <button
                onClick={handleLogout}
                title="Log out"
                className="p-1.5 rounded-lg hover:text-white hover:bg-zinc-800 transition"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Search bar */}
          <div className="px-3 py-2 border-b border-zinc-800/40">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                value={sidebarSearch}
                onChange={(e) => setSidebarSearch(e.target.value)}
                placeholder="Search"
                className="w-full bg-[#141518] text-white placeholder-zinc-500 rounded-lg pl-9 pr-8 py-1.5 text-xs outline-none focus:ring-1 focus:ring-[#2c6bed] border border-zinc-800/80 transition"
              />
              {sidebarSearch && (
                <button
                  onClick={() => setSidebarSearch("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Conversation list */}
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
            {convsLoading && (
              <div className="flex justify-center py-10">
                <Loader2 className="w-6 h-6 animate-spin text-[#2c6bed]" />
              </div>
            )}

            {!convsLoading && filteredConvs.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <MessageCircle className="w-8 h-8 text-zinc-600 mb-2" />
                <p className="text-zinc-400 text-xs">
                  {sidebarSearch ? "No conversations match your search" : "No chats yet"}
                </p>
                {!sidebarSearch && (
                  <button
                    onClick={() => setShowNewConv(true)}
                    className="mt-3 text-[#2c6bed] hover:underline text-xs font-medium"
                  >
                    Start a chat
                  </button>
                )}
              </div>
            )}

            {filteredConvs.map((conv) => (
              <ConversationItem
                key={conv.id}
                conv={conv}
                myUserId={myId}
                isActive={conv.id === activeConvId}
                isTyping={Boolean(typingMap[conv.id])}
                onClick={() => setActiveConvId(conv.id)}
              />
            ))}
          </div>
        </aside>

        {/* ── MAIN CHAT AREA ── */}
        <main
          className={`flex-1 flex flex-col min-w-0 bg-[#111215] ${
            !activeConv ? "hidden sm:flex" : "flex"
          }`}
        >
          {activeConv ? (
            <ChatArea
              key={activeConv.id}
              conv={activeConv}
              myUserId={myId}
              onBack={() => setActiveConvId(null)}
            />
          ) : (
            <EmptyState onNewChat={() => setShowNewConv(true)} />
          )}
        </main>
      </div>
    </>
  );
}
