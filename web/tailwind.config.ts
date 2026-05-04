import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        speed: "#F59E0B",
        batch: "#3B82F6",
        merged: "#10B981",
      },
    },
  },
  plugins: [],
};
export default config;
