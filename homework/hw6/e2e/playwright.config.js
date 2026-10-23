import { defineConfig, devices } from '@playwright/test';

const PORT = 3100;

export default defineConfig({
  testDir: './tests',
  // 所有測試共用同一台伺服器（同一份資料），所以一次只跑一個
  workers: 1,
  fullyParallel: false,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  // Playwright 會先幫我們啟動 Rust 伺服器，等 /api/health 回 200 才開始測
  webServer: {
    command: 'cargo run --manifest-path ../server/Cargo.toml',
    url: `http://127.0.0.1:${PORT}/api/health`,
    env: { PORT: String(PORT) },
    timeout: 300_000, // 第一次要編譯 Rust，給久一點
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
  },
});
