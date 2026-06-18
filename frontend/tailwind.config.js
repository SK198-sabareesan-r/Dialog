/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        dialog: {
          red:        '#ff4e2e',
          'red-d':    '#ed1c24',
          'red-lt':   '#FFF1F0',
          'red-muted':'rgba(255,78,46,0.08)',
          magenta:    '#9F215D',
          pink:       '#e34984',
          orange:     '#f36d24',
          blue:       '#0079C0',
          white:      '#FFFFFF',
          bg:         '#f4f5f6',
          sidebar:    '#FFFFFF',
          border:     '#dee2e6',
          text:       '#343a40',
          muted:      '#6c757d',
          faint:      '#979797',
          success:    '#28a745',
          warning:    '#ffc107',
          error:      '#dc3545',
          online:     '#28a745',
          dark:       '#333333',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'dialog-sm': '8px',
        'dialog-md': '12px',
        'dialog-lg': '16px',
        'dialog-xl': '20px',
      },
      boxShadow: {
        'dialog-sm': '0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.03)',
        'dialog-md': '0 2px 8px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04)',
        'dialog-lg': '0 4px 16px rgba(0,0,0,0.08), 0 12px 40px rgba(0,0,0,0.06)',
        sidebar:     '2px 0 8px rgba(0,0,0,0.04)',
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.4s ease-out both',
        'fade-in': 'fadeIn 0.3s ease-out both',
        'slide-in-left': 'slideInLeft 0.35s ease-out both',
      },
    },
  },
  plugins: [],
};
