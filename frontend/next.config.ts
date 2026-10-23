import type { NextConfig } from "next";

// Built as static files (`out/`) that the FastAPI backend serves, so the whole app
// still runs as one process. During `npm run dev` the pages call the API directly
// at NEXT_PUBLIC_API_URL (see .env.development).
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
