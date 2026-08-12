import type { Course, Document, Message } from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail || "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  config: () => request<{ ai_configured: boolean; chat_model: string; embedding_model: string }>("/api/config"),
  courses: () => request<Course[]>("/api/courses"),
  createCourse: (name: string) => request<Course>("/api/courses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  }),
  deleteCourse: (id: number) => request<void>(`/api/courses/${id}`, { method: "DELETE" }),
  documents: (courseId: number) => request<Document[]>(`/api/courses/${courseId}/documents`),
  upload: (courseId: number, kind: Document["kind"], file: File) => {
    const form = new FormData();
    form.append("kind", kind);
    form.append("file", file);
    return request<Document>(`/api/courses/${courseId}/documents`, { method: "POST", body: form });
  },
  deleteDocument: (id: number) => request<void>(`/api/documents/${id}`, { method: "DELETE" }),
  messages: (courseId: number) => request<Message[]>(`/api/courses/${courseId}/messages`),
  clearMessages: (courseId: number) => request<void>(`/api/courses/${courseId}/messages`, { method: "DELETE" }),
  ask: (courseId: number, query: string, documentId: number | null) =>
    request<{ answer: string; citations: Message["citations"] }>(`/api/courses/${courseId}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, document_id: documentId }),
    }),
};
