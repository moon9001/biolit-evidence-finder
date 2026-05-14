import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Frontend dev server runs on 5173 and proxies /api and /viewer-pdf to backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
