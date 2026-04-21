import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          500: '#2563eb',
          600: '#1d4ed8',
          900: '#1e3a8a',
        },
        up: '#dc2626',    // 상승 (Korean convention: red)
        down: '#2563eb',  // 하락 (Korean convention: blue)

        // macOS Sonoma light surface system
        surface: {
          DEFAULT: '#ededed',  // page background (soft gray)
          card: '#ffffff',     // main card
          inner: '#f4f4f5',    // nested mini card
          border: '#d4d4d8',   // subtle divider
        },
        ink: {
          DEFAULT: '#18181b',  // primary text
          muted: '#52525b',
          subtle: '#a1a1aa',
        },
        traffic: {
          red: '#ff5f57',
          yellow: '#febc2e',
          green: '#28c840',
        },
      },
      fontFamily: {
        sans: ['"Pretendard Variable"', 'Pretendard', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        mac: '0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)',
        'mac-lg': '0 4px 12px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.04)',
      },
    },
  },
  plugins: [],
} satisfies Config
