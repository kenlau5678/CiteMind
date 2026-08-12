/// <reference types="vite/client" />

declare module "pdfjs-dist/build/pdf.worker.min.mjs?worker" {
  const WorkerConstructor: { new (options?: WorkerOptions): Worker };
  export default WorkerConstructor;
}

declare module "*.css";
