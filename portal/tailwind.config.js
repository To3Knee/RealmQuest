export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: { 'obsidian': '#050505', 'void': '#0a0a0c', 'gold': '#fbbf24' },
      fontFamily: { sans: ['Inter', 'sans-serif'], cinematic: ['Cinzel', 'serif'], mono: ['JetBrains Mono', 'monospace'] },
      animation: { 'fade-in': 'fadeIn 0.5s ease-out' },
      keyframes: { fadeIn: { '0%': { opacity: '0', transform: 'translateY(10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } } }
    },
  },
  plugins: [],
}
