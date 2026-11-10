/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "#2563eb",
          "blue-hover": "#1d4ed8",
          "blue-subtle": "#eff6ff",
        },
        navy: {
          900: "#111827",
          950: "#0b0f17",
        },
      },
    },
  },
  plugins: [],
};

