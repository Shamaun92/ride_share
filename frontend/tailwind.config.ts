import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0D1522",
        ink2: "#152033",
        paper: "#F5F4EF",
        card: "#FFFFFF",
        teal: { DEFAULT: "#0FA3A3", deep: "#0B7E7E" },
        jade: "#16C172",
        amber: "#F6A623",
        slate2: "#51607A",
        line: "#E6E3DB",
        danger: "#E5484D",
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: { xl2: "14px" },
      boxShadow: {
        card: "0 1px 2px rgba(13,21,34,0.04), 0 8px 24px -12px rgba(13,21,34,0.12)",
        console: "0 24px 60px -24px rgba(13,21,34,0.45)",
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
      },
      animation: {
        ping2: "ping2 1.8s cubic-bezier(0,0,0.2,1) infinite",
        rise: "rise 0.4s ease-out both",
      },
    },
  },
  plugins: [],
};
export default config;
