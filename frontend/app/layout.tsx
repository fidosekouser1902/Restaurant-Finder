import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CraveAI — AI Restaurant Finder",
  description: "Personalized restaurant recommendations powered by AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
