/**
 * Contacts service — wraps contact-related API calls.
 */

import { apiClient } from "@/lib/api-client";
import type { Contact, ContactUser, AddContactRequest } from "@/types";

export const contactsService = {
  list: () => apiClient.get<Contact[]>("/contacts"),

  add: (data: AddContactRequest) =>
    apiClient.post<Contact>("/contacts", data),

  remove: (contactUserId: string) =>
    apiClient.delete<void>(`/contacts/${contactUserId}`),

  search: (query: string) =>
    apiClient.get<ContactUser[]>(
      `/users/search?q=${encodeURIComponent(query)}`
    ),
};
