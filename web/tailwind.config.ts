import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#050a14",
        foreground: "#f1f5f9",
        brand: {
          DEFAULT: "#3b82f6",
          bright: "#60a5fa",
          deep: "#1d4ed8",
          soft: "#93c5fd",
          muted: "#1e3a5f",
        },
        card: {
          DEFAULT: "rgba(10, 22, 48, 0.55)",
          border: "rgba(96, 165, 250, 0.18)",
        },
        cyber: {
          green: "#10b981",
          emerald: "#059669",
          cyan: "#06b6d4",
          blue: "#3b82f6",
          purple: "#8b5cf6",
          rose: "#f43f5e",
          amber: "#f59e0b",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-jakarta)",
          "Plus Jakarta Sans",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        display: [
          "var(--font-grotesk)",
          "Space Grotesk",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          "var(--font-mono)",
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        "neon-green": "0 0 20px -3px rgba(16, 185, 129, 0.35)",
        "neon-cyan": "0 0 20px -3px rgba(6, 182, 212, 0.35)",
        "neon-rose": "0 0 20px -3px rgba(244, 63, 94, 0.35)",
        "neon-amber": "0 0 20px -3px rgba(245, 158, 11, 0.35)",
        "neon-blue": "0 0 28px -4px rgba(59, 130, 246, 0.45)",
        glass: "0 18px 40px -24px rgba(37, 99, 235, 0.45)",
      },
      animation: {
        "pulse-fast": "pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "ping-slow": "ping 2.5s cubic-bezier(0, 0, 0.2, 1) infinite",
        "fade-up": "fadeUp 0.6s ease-out both",
        "glow-pulse": "glowPulse 3.5s ease-in-out infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        glowPulse: {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "0.9" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
