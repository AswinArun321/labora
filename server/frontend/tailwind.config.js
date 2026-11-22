/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef4ff',
          100: '#dbe6fe',
          200: '#bfd5fe',
          300: '#93bcfd',
          400: '#609afa',
          500: '#3b6cf6',
          600: '#2852e0',
          700: '#1f40b5',
          800: '#1d3592',
          900: '#1c3074',
        },
      },
    },
  },
  plugins: [],
};
