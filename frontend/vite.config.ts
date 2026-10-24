import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  resolve: {
    alias: { "@brand": fileURLToPath(new URL("../brand-kit/src/index.ts", import.meta.url)) },
    // brand-kit has its own node_modules; make its components use this app's single React.
    dedupe: ["react", "react-dom"],
  },
  server: {
    fs: { allow: [".."] },
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
