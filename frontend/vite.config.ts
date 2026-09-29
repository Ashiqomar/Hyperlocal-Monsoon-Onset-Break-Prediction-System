import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  // Read BACKEND_URL from the shell or a .env file (prefix "" = not only VITE_* vars).
  const env = { ...loadEnv(mode, process.cwd(), ""), ...process.env };

  // The browser calls /api/*, and Vite forwards it to the backend. This avoids
  // CORS in dev and lets Docker point at the `backend` service by name.
  const backendUrl = env.BACKEND_URL ?? "http://localhost:8000";

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: true,
      port: 5173,
      proxy: {
        "/api": {
          target: backendUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
