import typography from '@tailwindcss/typography';

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Premium Light Theme (Inspired by Apple/FinPoint/Twisty)
        bg: {
          canvas: '#F6F8FA',      // Soft off-white canvas
          surface: '#FFFFFF',     // Pure white elevated surface
          subtle: '#EDF1F5',      // For secondary panels
          inverse: '#111111',     // Deep black for inverse elements
          hover: '#F1F4F8',       // Hover states
        },
        text: {
          ink: '#111827',         // Deep charcoal for primary text
          body: '#4B5563',        // Neutral grey for body
          muted: '#9CA3AF',       // Light grey for secondary/muted
          faint: '#D1D5DB',       // Faint text
        },
        border: {
          light: '#F3F4F6',       // Very subtle borders
          mid: '#E5E7EB',         // Standard borders
          strong: '#D1D5DB',      // Strong borders
        },
        // Accents - Bold, sophisticated orange-red and sleek teal
        accent: {
          DEFAULT: '#FF5733',     // Vibrant FinPoint Orange-Red
          subtle: 'rgba(255, 87, 51, 0.08)',
          hover: '#E64A2E',
          teal: '#00D1FF',        // Electric teal for secondary highlights
        },
        // Refined status colors
        status: {
          success: '#10B981',     // Emerald
          warning: '#F59E0B',     // Amber
          danger: '#EF4444',      // Red
          info: '#3B82F6',        // Blue
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'card': '0 10px 25px -5px rgba(0, 0, 0, 0.04), 0 8px 10px -6px rgba(0, 0, 0, 0.04)',
        'glow': '0 0 15px rgba(255, 87, 51, 0.15)',
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      transitionTimingFunction: {
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'spring': 'cubic-bezier(0.175, 0.885, 0.32, 1.2)',
      }
    },
  },
  plugins: [
    typography,
  ],
}
