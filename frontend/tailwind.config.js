/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'calendar-bg': '#000000',
        'calendar-text-cream': '#fcecc9',
        'calendar-text-light': '#f7f9f7',
        'calendar-text-gray': '#6a7282',
        'calendar-border': '#606060',
        'calendar-card-bg': '#f7f9f7',
        'calendar-close': '#888888',
      },
    },
  },
  plugins: [],
}

