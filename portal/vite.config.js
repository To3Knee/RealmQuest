//===============================================================
//Script Name: vite.config.js
//Script Location: /opt/RealmQuest/portal/vite.config.js
//Date: 01/26/2026
//Created By: T03KNEE
//Github: https://github.com/To3Knee/RealmQuest
//Version: 1.0.2
//About: Vite config with FQDN Whitelisting for Pangolin/Reverse Proxy
//===============================================================

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    
    // SECURITY: Whitelist the FQDN to prevent "Blocked Request" errors.
    // Setting to 'true' allows all hosts, which is standard for apps 
    // sitting behind a trusted Reverse Proxy (Pangolin).
    allowedHosts: true,

    // Container stability: polling can cause false "file changed" events -> repeated refresh
    watch: {
      usePolling: false,
    },

    // Prevent HMR from repeatedly forcing client reloads in containerized environments
    hmr: false,
  }
})