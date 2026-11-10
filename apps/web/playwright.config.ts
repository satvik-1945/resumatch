import { defineConfig } from "@playwright/test";
import { loadEnvConfig } from "@next/env";
import path from "node:path";

loadEnvConfig(path.resolve(process.cwd(), "../.."));
const database = process.env.TEST_DATABASE_URL;
if (!database || !new URL(database.replace("postgresql+psycopg:", "postgresql:")).pathname.endsWith("_test")) {
  throw new Error("Set TEST_DATABASE_URL to a separate migrated database ending in _test");
}

export default defineConfig({
  testDir: "./tests",
  use: { baseURL: "http://localhost:3001", trace: "retain-on-failure" },
  workers: 1,
  // Dedicated test ports/database; fail if occupied instead of testing an unrelated server.
  webServer: [
    {
      command: "uv run uvicorn resumatch.main:app --host 127.0.0.1 --port 8001",
      cwd: "../..",
      url: "http://127.0.0.1:8001/api/health/ready",
      env: { DATABASE_URL: database, WEB_ORIGIN: "http://localhost:3001", WEB_ADDITIONAL_ORIGINS: '["http://127.0.0.1:3001"]', COOKIE_SECURE: "false", REGISTRATION_ENABLED: "true", LLM_API_KEY: "" },
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --port 3001",
      url: "http://localhost:3001",
      env: { API_ORIGIN: "http://127.0.0.1:8001", RESUMATCH_E2E: "1" },
      timeout: 120_000,
    },
  ],
});
