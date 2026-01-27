//===============================================================
// Script Name: vite.config.js
// Script Location: /opt/RealmQuest/portal/vite.config.js
// Date: 2026-01-26
// Version: 18.22.0
// About: Added allowedHosts for FQDN (Pangolin Proxy Support)
//===============================================================

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on all IPs (Docker Requirement)
    host: true, 
    // Internal Container Port
    port: 5173, 
    strictPort: true,
    // FIX: Whitelist your FQDN so Vite accepts the Proxy traffic
    allowedHosts: [
      "portal.realmquest.net",
      "localhost",
      "127.0.0.1"
    ],
    // Polling for Docker volume stability
    watch: {
      usePolling: true,
      interval: 100,
    }
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})