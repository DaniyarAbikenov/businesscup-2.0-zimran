import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// In Docker the frontend reaches the API at http://backend:8000; locally at localhost.
const api = process.env.API_URL || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Bind mounts on macOS/Windows do not emit file events; polling keeps hot reload working.
    watch: process.env.CHOKIDAR_USEPOLLING ? { usePolling: true, interval: 300 } : undefined,
    proxy: { '/api': { target: api, changeOrigin: false }, '/health': { target: api } },
  },
});
