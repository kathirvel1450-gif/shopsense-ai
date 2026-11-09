import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  envDir: fileURLToPath(new URL('..', import.meta.url)),
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      input: { dashboard: fileURLToPath(new URL('./index.html', import.meta.url)), marketplace: fileURLToPath(new URL('./marketplace.html', import.meta.url)) },
      output: { manualChunks(id) { const normalized = id.replaceAll('\\\\', '/'); if (/\/node_modules\/(recharts|d3-[^/]+)\//.test(normalized)) return 'charts'; } },
    },
  },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.js' },
});
