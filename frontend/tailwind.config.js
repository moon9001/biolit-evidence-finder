/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        forest: {
          50: '#f1f7f3',
          100: '#daeae0',
          200: '#b6d6c2',
          300: '#8bbd9d',
          400: '#5fa178',
          500: '#3d8559',
          600: '#2c6644',
          700: '#234f37',
          800: '#1c3e2c',
          900: '#142d20',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'PingFang SC',
          'Microsoft YaHei', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
};
