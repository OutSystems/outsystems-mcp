import { defineConfig, devices } from '@playwright/test';
import 'dotenv/config';

const baseURL = (process.env.APP_BASE_URL || '{{BASE_URL}}').replace(/\/$/, '') + '/';
// scripts/run.mjs points a run of a few requirements at evidence/subset, so it never
// overwrites the full run's report and matrix.
const evidence = process.env.EVIDENCE_DIR ?? 'evidence';
// scripts/screens.mjs, the build loop's replay after each publish, needs a verdict, not
// evidence: no trace or video, a screenshot only of a failure.
const screensRun = process.env.SCREENS_RUN === '1';

export default defineConfig({
  testDir: './tests',
  outputDir: `./${evidence}/artifacts`,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  workers: 4,
  // A leftover test.only would run one test and report success.
  forbidOnly: true,
  // A retry shows a test that only fails sometimes as flaky, and a flaky test fails the
  // run: it is a difference to fix, never a pass.
  retries: 1,
  failOnFlakyTests: true,
  reporter: [
    ['list'],
    ['html', { outputFolder: `${evidence}/html-report`, open: 'never' }],
    ['json', { outputFile: `${evidence}/results.json` }],
  ],
  use: {
    baseURL,
    // Evidence, not pass/fail checks: keep a trace and a screenshot for every test. The trace
    // keeps DOM snapshots (replayable step by step) but not the screencast frames, which halves
    // its size. No video: the trace and the screenshot already show what happened, and video
    // makes every run and the handover zip much heavier. Set video: 'on' if a customer asks.
    // A screens run (npm run screens) keeps no trace and a screenshot only of a failure.
    trace: screensRun ? 'off' : { mode: 'on', screenshots: false, snapshots: true, sources: true },
    screenshot: screensRun ? 'only-on-failure' : 'on',
    video: 'off',
    viewport: { width: 1440, height: 900 },
    locale: '{{LOCALE}}',
    timezoneId: '{{TIMEZONE}}',
    acceptDownloads: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
  ],
});
