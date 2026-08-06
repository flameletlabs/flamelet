import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Dev host comes from the environment so no contributor's private hostname is
    // baked in. Set FLAMELET_DEV_HOST to reach the dev server by name from another
    // machine; unset means localhost, which is what a fresh clone should get.
    allowedHosts: [process.env.FLAMELET_DEV_HOST, 'localhost', '127.0.0.1'].filter(Boolean),
    hmr: {
      protocol: 'ws',
      host: process.env.FLAMELET_DEV_HOST || 'localhost',
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
