import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "Shohojatri — ride dispatch for Dhaka",
  description: "Request a ride and watch it move, live. A real-time ride-hailing console.",
};

// Fonts are loaded at runtime via the stylesheet below (the CSS variables in
// globals.css reference these families). This avoids build-time font fetching
// and works in any environment; swap for next/font/google where preferred.
const FONTS =
  "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&family=Space+Grotesk:wght@500;700&display=swap";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href={FONTS} />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
