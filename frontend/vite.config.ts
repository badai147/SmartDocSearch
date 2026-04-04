import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // 让前端直接用 /api 调用后端
      "/api": "http://localhost:8000",
    },
  },
});

