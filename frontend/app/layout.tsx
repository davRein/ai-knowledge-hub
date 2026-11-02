import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { WorkspaceShell } from "../components/workspace-shell";

export const metadata: Metadata = {
  title: "AI Knowledge Hub | Private knowledge workspace",
  description: "Private document-grounded answers with source references.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <WorkspaceShell>{children}</WorkspaceShell>
      </body>
    </html>
  );
}
