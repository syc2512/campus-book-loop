import { defineConfig, devices } from "@playwright/test";

const API_PORT = Number(process.env.E2E_API_PORT ?? 8010);
const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 3010);
// Point this at the Python interpreter that has apps/api installed, e.g.
// E2E_PYTHON=../.venv/Scripts/python.exe npm run test:e2e
const PYTHON = process.env.E2E_PYTHON ?? "python";

const apiUrl = `http://127.0.0.1:${API_PORT}`;
const webUrl = `http://127.0.0.1:${WEB_PORT}`;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: webUrl,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${PYTHON} -m uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: "../api",
      url: `${apiUrl}/health`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: {
        DATABASE_URL: "sqlite://",
        SEED_ON_STARTUP: "true",
        AUTO_CREATE_SCHEMA: "true",
        TOKEN_SECRET: "e2e-secret-not-for-production",
        UPLOAD_DIR: ".e2e-uploads",
        CORS_ORIGINS: `${webUrl},http://localhost:${WEB_PORT}`,
      },
    },
    {
      command: `npm run dev -- --hostname 127.0.0.1 --port ${WEB_PORT}`,
      url: webUrl,
      timeout: 180_000,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_BASE_URL: `${apiUrl}/api/v1`,
      },
    },
  ],
});
