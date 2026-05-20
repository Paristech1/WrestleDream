import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import devApiPlugin from './devApiPlugin.js';

export default defineConfig({
  plugins: [devApiPlugin(), react()],
  server: {
    port: 5173,
  },
});
