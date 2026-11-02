import type { Metadata } from "next";
import { DocumentsPanel } from "../../components/documents-panel";

export const metadata: Metadata = { title: "Documents | AI Knowledge Hub" };

export default function DocumentsPage() {
  return <DocumentsPanel />;
}
