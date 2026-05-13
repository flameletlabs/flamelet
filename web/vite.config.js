import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: '0.0.0.0',
    hmr: {
      protocol: 'ws',
      host: '192.168.160.249',
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
