/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      // "Civic" palette: warm off-white paper, near-black ink and a single deep
      // green accent. Every text/background pairing below meets WCAG AA.
      colors: {
        paper: "#F6F4EE",
        surface: "#FFFFFF",
        ink: {
          DEFAULT: "#1C2024",
          soft: "#4A525C",
        },
        line: "#D6D2C8",
        brand: {
          DEFAULT: "#0B5D3B",
          dark: "#08472D",
          tint: "#E3F0E8",
        },
        alert: "#A4261C",
      },
      fontFamily: {
        // Atkinson Hyperlegible was designed for low-vision readers. The
        // system fonts are the fallback if the web font can't load.
        sans: [
          '"Atkinson Hyperlegible"',
          "system-ui",
          '"Segoe UI"',
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
