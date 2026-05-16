import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: ['dev.baar', 'localhost', '127.0.0.1'],
    hmr: {
      protocol: 'ws',
      host: 'dev.baar',
      port: 5173
    },
    proxy: {
      '/api': 'http://localhost:7070'
    }
  },
  build: {
    outDir: 'dist',
  }
});
