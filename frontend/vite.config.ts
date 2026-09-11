import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev server talks to the FastAPI backend without CORS friction.
    // `/api` is the canonical prefix. The bare ORCA 2.0 root paths are also
    // proxied so any direct root call (or older code path) still reaches the
    // backend in dev instead of being served index.html — see INT-001.
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/plan": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/trace": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/state": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/voyages": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/alerts": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/voice": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
