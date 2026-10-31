import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// In development the API runs on Django (port 8000); proxying keeps the SPA same-origin,
// exactly like production where Django serves both.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  build: {
    sourcemap: true,
    // The MUI vendor chunk (material + date pickers) is ~550 kB minified, ~165 kB gzipped.
    chunkSizeWarningLimit: 600,
    rolldownOptions: {
      output: {
        // Stable vendor chunks download in parallel and stay cached across app deploys.
        // Leaflet is not listed: it stays in the lazily loaded map chunk.
        codeSplitting: {
          groups: [
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
            {
              name: 'mui',
              test: /node_modules[\\/](@mui|@emotion|@popperjs|react-transition-group|stylis)[\\/]/,
            },
          ],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
