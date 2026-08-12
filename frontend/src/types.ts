export type Course = {
  id: number;
  name: string;
  created_at: string;
  document_count?: number;
};

export type Document = {
  id: number;
  course_id: number;
  title: string;
  filename: string;
  kind: "lecture" | "notes" | "paper";
  page_count: number;
  size_bytes: number;
  status: string;
};

export type Citation = {
  number: number;
  chunk_id: number;
  document_id: number;
  title: string;
  page_number: number;
  content: string;
};

export type Message = {
  id?: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
};

