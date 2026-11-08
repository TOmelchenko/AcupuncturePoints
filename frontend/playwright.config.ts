import { execSync } from 'node:child_process'
import { defineConfig, devices } from '@playwright/test'

/**
 * Browser tests against the full local stack: Vite dev server, the backend with
 * the offline demo AI, and local Supabase (Auth, database with seed data,
 * Storage, Mailpit). Run `make supabase-start db-setup db-seed` first, or
 * `make e2e`, which does that.
 */

function supabaseSettings() {
  if (process.env.SUPABASE_ANON_KEY && process.env.SUPABASE_SERVICE_ROLE_KEY) return
  const status = JSON.parse(
    execSync('npx -y supabase@3.0.0 status -o json', { cwd: '..', encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }),
  )
  process.env.SUPABASE_ANON_KEY = status.ANON_KEY
  process.env.SUPABASE_SERVICE_ROLE_KEY = status.SERVICE_ROLE_KEY
}
supabaseSettings()
process.env.SUPABASE_URL ??= 'http://127.0.0.1:54321'
process.env.MAILPIT_URL ??= 'http://127.0.0.1:54324'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    {
      command: 'uv run uvicorn app.main:app --port 8000',
      cwd: '../backend',
      url: 'http://localhost:8000/api/health',
      reuseExistingServer: !process.env.CI,
      env: {
        AI_PROVIDER: 'fake',
        SUPABASE_URL: process.env.SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY!,
        DATABASE_URL: process.env.DATABASE_URL ?? 'postgresql://postgres:postgres@127.0.0.1:54322/postgres',
      },
    },
    {
      command: 'npx vite --port 5173 --strictPort',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      env: {
        VITE_SUPABASE_URL: process.env.SUPABASE_URL,
        VITE_SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY!,
        VITE_API_BASE_URL: '',
      },
    },
  ],
})
