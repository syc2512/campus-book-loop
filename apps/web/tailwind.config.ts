import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#173638",
        paper: "#eef1e8",
        moss: "#2f6558",
        marigold: "#edbd45",
        brick: "#bd4f35",
        chalk: "#f9faf4",
        fog: "#758480",
      },
      fontFamily: {
        display: ['"Noto Serif SC"', '"Source Han Serif SC"', '"Songti SC"', "serif"],
        sans: ['"Noto Sans SC"', '"Source Han Sans SC"', "Aptos", "sans-serif"],
      },
      boxShadow: {
        paper: "0 20px 60px rgba(23, 54, 56, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
