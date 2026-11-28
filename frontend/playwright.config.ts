import { defineConfig } from '@playwright/test'
import { existsSync } from 'node:fs'

const localPython = process.platform === 'win32' ? '../backend/.venv/Scripts/python.exe' : '../backend/.venv/bin/python'
const python = process.env.BLUEGRID_PYTHON ?? (existsSync(localPython) ? localPython : 'python')

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 }, headless: true,
    launchOptions: { args: process.env.CI ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : [] },
  },
  webServer: [
    { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
    { command: `"${python}" ../backend/run.py`, url: 'http://127.0.0.1:5000/api/health', reuseExistingServer: !process.env.CI },
  ],
})
