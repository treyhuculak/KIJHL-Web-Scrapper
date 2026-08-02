import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Send /api calls to the FastAPI server so the app can use relative URLs.
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8100',
    },
  },
})
