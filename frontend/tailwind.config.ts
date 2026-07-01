import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B1220",
        ink2: "#161F30",
        paper: "#F4F6F8",
        card: "#FFFFFF",
        teal: { DEFAULT: "#0EA5A5", deep: "#0B7E7E", soft: "#E6F6F6" },
        jade: "#12B981",
        amber: "#F59E0B",
        slate2: "#5A6B85",
        line: "#E7EAF0",
        danger: "#EF4444",
        map: { bg: "#E7ECF2", street: "#D6DCE6", block: "#DDE3EC", park: "#D6E7D8" },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: { xl2: "14px", "2xl": "18px", "3xl": "26px" },
      boxShadow: {
        card: "0 1px 2px rgba(11,18,32,0.04), 0 10px 30px -16px rgba(11,18,32,0.18)",
        console: "0 24px 60px -24px rgba(11,18,32,0.45)",
        sheet: "0 -8px 40px -12px rgba(11,18,32,0.22), 0 -1px 0 rgba(231,234,240,0.9)",
        float: "0 8px 30px -8px rgba(11,18,32,0.22)",
        pin: "0 4px 12px -2px rgba(11,18,32,0.35)",
      },
      keyframes: {
        ping2: {
          "0%": { transform: "scale(1)", opacity: "0.55" },
          "100%": { transform: "scale(2.6)", opacity: "0" },
        },
        rise: {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        sheet: {
          "0%": { transform: "translateY(24px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        ping2: "ping2 1.8s cubic-bezier(0,0,0.2,1) infinite",
        rise: "rise 0.4s ease-out both",
        sheet: "sheet 0.45s cubic-bezier(0.22,1,0.36,1) both",
        shimmer: "shimmer 1.6s infinite",
      },
    },
  },
  plugins: [],
};
export default config;
