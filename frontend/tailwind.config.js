/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Neo-brutalism vibrant color palette
        'neo-yellow': '#FFEB3B',
        'neo-pink': '#FF006E',
        'neo-cyan': '#00F5FF',
        'neo-lime': '#B2FF59',
        'neo-orange': '#FF6B35',
        'neo-purple': '#8338EC',
        'neo-blue': '#3A86FF',
        'neo-black': '#0A0A0A',

        // Claude theme colors
        'claude': {
          'bg': '#F5F5F0',
          'surface': '#FFFFFF',
          'border': '#E5E5E0',
          'primary': '#CC785C',
          'primary-hover': '#B86A4E',
          'text': '#2C2A29',
          'text-secondary': '#6B6B68',
          'sidebar': '#F0EFEA',
          'user-msg': '#E8DED3',
          'assistant-msg': '#FFFFFF',
          'accent': '#9B87F5',
        },
      },
      boxShadow: {
        'brutal': '6px 6px 0px 0px #0A0A0A',
        'brutal-lg': '8px 8px 0px 0px #0A0A0A',
        'brutal-sm': '4px 4px 0px 0px #0A0A0A',
        'brutal-hover': '10px 10px 0px 0px #0A0A0A',
        'claude': '0 1px 3px 0 rgb(0 0 0 / 0.1)',
        'claude-lg': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slideDown': 'slideDown 0.3s ease-out',
        'wiggle': 'wiggle 0.3s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': {
            opacity: '0',
            transform: 'translateY(10px)',
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        slideDown: {
          '0%': {
            opacity: '0',
            transform: 'translateY(-20px)',
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(-2deg)' },
          '50%': { transform: 'rotate(2deg)' },
        },
      },
    },
  },
  plugins: [],
}
