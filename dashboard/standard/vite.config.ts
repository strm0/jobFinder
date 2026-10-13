import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The built page is served by `dashboard/serve.py --ui standard`. `npm run dev` is only for
// working on the page: it stays on localhost and passes /api through to the Python server.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8787", "/demo": "http://127.0.0.1:8787" },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
