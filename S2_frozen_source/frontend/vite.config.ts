import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Frontend dev server proxies /api to the backend. The timeout/proxyTimeout
// values disable the default idle cap so large PDF uploads aren't killed.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Accept any Host header. Vite 5+ blocks unknown hosts by default; for
    // a research prototype intended to run on LAN / behind a reverse proxy
    // we allow all so users can put it behind any custom domain or tunnel.
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0,
        ws: false,
      },
    },
  },
});
