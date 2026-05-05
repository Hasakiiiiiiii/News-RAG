import type { Config } from "tailwindcss";

const config: Config = {
  // BẮT BUỘC PHẢI CÓ KHỐI CONTENT NÀY
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#0f172a',    // Sidebar background
          primary: '#4f46e5', // Indigo button/active
          accent: '#10b981',  // Emerald status
        }
      }
    },
  },
  plugins: [],
};

// Bắt buộc phải export ra thì Next.js mới đọc được
export default config;