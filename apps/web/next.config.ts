import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "node:path";

// Share the root .env with the API without exposing server configuration to clients.
loadEnvConfig(path.resolve(process.cwd(), "../.."));

const nextConfig: NextConfig = {
  // Browser checks must not contend with an already running local dev server.
  distDir: process.env.RESUMATCH_E2E === "1" ? ".next-e2e" : ".next",
  async rewrites() {
    return [{
      source: "/api/:path*",
      destination: `${process.env.API_ORIGIN ?? "http://127.0.0.1:8000"}/api/:path*`,
    }];
  },
};

export default nextConfig;
