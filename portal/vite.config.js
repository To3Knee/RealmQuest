//===============================================================
//Script Name: vite.config.js
//Script Location: /opt/RealmQuest/portal/vite.config.js
//Date: 01/25/2026
//Created By: T03KNEE
//Github: https://github.com/To3Knee/RealmQuest
//Version: 1.0.1
//About: Vite server stability (disable polling/HMR to prevent reload loops in containers)
//===============================================================

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,

    // Container stability: polling can cause false "file changed" events -> repeated refresh
    watch: {
      usePolling: false,
    },

    // Prevent HMR from repeatedly forcing client reloads in containerized environments
    hmr: false,
  }
})
