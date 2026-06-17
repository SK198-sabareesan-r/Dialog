/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        dialog: {
          pink:       '#E91E8C',   // primary — active nav, buttons, chat bubbles
          'pink-d':   '#C91578',   // hover
          'pink-lt':  '#FDF0F7',   // light pink bg tint
          white:      '#FFFFFF',
          bg:         '#F5F6F8',   // page background
          sidebar:    '#FFFFFF',   // sidebar background
          border:     '#E8EAF0',
          text:       '#1A1A2E',
          muted:      '#6B7280',
          faint:      '#9CA3AF',
          success:    '#059669',
          warning:    '#D97706',
          error:      '#DC2626',
          online:     '#22C55E',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card:        '0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)',
        'card-hover':'0 4px 12px rgba(0,0,0,0.09), 0 8px 24px rgba(0,0,0,0.06)',
        sidebar:     '2px 0 8px rgba(0,0,0,0.06)',
      },
    },
  },
  plugins: [],
};
