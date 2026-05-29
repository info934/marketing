import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Creative OS Chat",
  description: "Chat-first AI workflow frontend for ecommerce creative generation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="cs">
      <body>{children}</body>
    </html>
  );
}
