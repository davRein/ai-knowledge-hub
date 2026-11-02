import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./portfolio",
  workers: 1,
  fullyParallel: false,
  timeout: 90_000,
  reporter: "list",
  outputDir: "test-results/portfolio",
  use: {
    baseURL: "http://127.0.0.1:3200",
    channel: "msedge",
    headless: true,
    trace: "off",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1100 } } },
    {
      name: "mobile",
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: {
    command: "npm run start -- --port 3200",
    url: "http://127.0.0.1:3200",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
