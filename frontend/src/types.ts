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
  processed_pages: number;
  size_bytes: number;
  status: "processing" | "ready" | "failed";
  error?: string | null;
};

export type Citation = {
  number: number;
  chunk_id: number;
  course_id?: number;
  course_name?: string;
  document_id: number;
  title: string;
  page_number: number;
  content: string;
  visual?: boolean;
};

export type Message = {
  id?: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  vision_used?: boolean;
};

export type AgentStep = {
  number: number;
  tool: "search_materials" | "read_page" | "inspect_page" | "finish";
  arguments: Record<string, string | number>;
  result_count: number;
  document_title?: string;
};

export type AgentCourse = {
  id: number;
  name: string;
  documents: { id: number; title: string; pages: number[] }[];
};

export type AgentResult = {
  answer: string;
  citations: Citation[];
  steps: AgentStep[];
  courses: AgentCourse[];
  insufficient: boolean;
  vision_used: boolean;
};

export type AgentStreamEvent =
  | { type: "status"; message: string }
  | { type: "step"; step: AgentStep }
  | { type: "answer_delta"; delta: string }
  | { type: "complete"; result: AgentResult }
  | { type: "error"; message: string };
