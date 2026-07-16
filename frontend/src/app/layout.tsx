import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "AURA - Autonomous University Response Assistant",
  description: "A free, self-hosted personal AI assistant for college students.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className="antialiased"
      >
        <Toaster position="top-right" toastOptions={{
          style: {
            background: '#1e293b',
            color: '#fff',
            border: '1px solid rgba(255,255,255,0.1)'
          }
        }} />
        {children}
      </body>
    </html>
  );
}
