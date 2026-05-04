import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Crypto Lambda Pipeline",
  description: "Data Engineer Portfolio — Lambda Architecture: Real-Time + Batch Crypto Pipeline",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="border-b border-gray-800 px-6 py-3 flex gap-6 items-center">
          <a href="/" className="text-lg font-bold tracking-tight">lambda-pipeline</a>
          <a href="/" className="text-sm text-gray-400 hover:text-white">Dashboard</a>
          <a href="/architecture" className="text-sm text-gray-400 hover:text-white">Architecture</a>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
