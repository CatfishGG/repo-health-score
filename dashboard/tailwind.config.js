/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0d1424',
        accent: '#FF6B35',
        surface: '#111827',
        border: '#1f2937',
        text: '#eef1f8',
        muted: '#6b7280',
      },
    },
  },
  plugins: [],
};