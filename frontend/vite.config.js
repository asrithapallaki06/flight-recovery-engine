import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During development, requests to /api are forwarded to the FastAPI server.
// That way the browser only ever talks to one address (localhost:5173).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': process.env.API_URL || 'http://localhost:8000',
    },
  },
})
