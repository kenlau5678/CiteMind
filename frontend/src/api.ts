import type { AgentResult, AgentStreamEvent, Course, Document, Message } from "./types";

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
  reorderDocuments: (courseId: number, documentIds: number[]) => request<void>(`/api/courses/${courseId}/documents/order`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: documentIds }),
  }),
  retryDocument: (id: number) => request<Document>(`/api/documents/${id}/retry`, { method: "POST" }),
  deleteDocument: (id: number) => request<void>(`/api/documents/${id}`, { method: "DELETE" }),
  messages: (courseId: number) => request<Message[]>(`/api/courses/${courseId}/messages`),
  clearMessages: (courseId: number) => request<void>(`/api/courses/${courseId}/messages`, { method: "DELETE" }),
  ask: (courseId: number, query: string, documentId: number | null, contextDocumentId: number | null, contextPageNumber: number | null) =>
    request<{ answer: string; citations: Message["citations"]; insufficient: boolean; vision_used: boolean }>(`/api/courses/${courseId}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, document_id: documentId, context_document_id: contextDocumentId, context_page_number: contextPageNumber }),
    }),
  explore: async (query: string, onEvent: (event: AgentStreamEvent) => void) => {
    const response = await fetch("/api/agent/explore/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(body.detail || "Knowledge exploration failed");
    }
    if (!response.body) throw new Error("Streaming is not supported by this browser");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let result: AgentResult | undefined;
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line) as AgentStreamEvent;
        onEvent(event);
        if (event.type === "error") throw new Error(event.message);
        if (event.type === "complete") result = event.result;
      }
      if (done) break;
    }
    if (!result) throw new Error("Knowledge exploration ended before completion");
    return result;
  },
};
