import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "StrandsOps SRE | Autonomous Cloud Self-Healing Command Center",
  description:
    "Autonomous self-healing cloud infrastructure powered by Strands Agents SDK & Amazon Bedrock Claude 3.5 Sonnet for AWS Account 3792-6468-7588.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen cyber-grid antialiased">
        {children}
      </body>
    </html>
  );
}
