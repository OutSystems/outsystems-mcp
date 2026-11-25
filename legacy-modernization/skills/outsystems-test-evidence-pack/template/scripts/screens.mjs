// Replays the tests of the screens a change touched: the build loop's check after each
// publish, instead of driving those screens again by hand.
//   npm run screens -- CustomerList CustomerDetail   tests/screens/<Screen>.spec.ts each
//   npm run screens                                  every test in the pack
// Light and quiet: no trace or video, a screenshot only of a failure, and one line per
// failing test or spec that failed to load, plus one short line of passing names
// (scripts/compact-reporter.mjs). Writes to evidence/screens/, so the full run's report
// and matrix stay as they were. Exits with the test run's status, or 2 when nothing could
// run (an unknown screen, Playwright not installed or its CLI not loadable). Uses node directly (no shell), so it
// behaves the same everywhere.

import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';

const DIR = 'tests/screens';
// Accept "A B", "A,B" and "A, B": the names come from the agent's list of touched screens.
const names = process.argv.slice(2).flatMap((a) => a.split(',')).map((s) => s.trim()).filter(Boolean);
const missing = names.filter((n) => !existsSync(`${DIR}/${n}.spec.ts`));
if (missing.length) {
  const have = existsSync(DIR) ? readdirSync(DIR).filter((f) => f.endsWith('.spec.ts')).map((f) => f.slice(0, -8)).sort() : [];
  console.error(`No screen tests for: ${missing.join(', ')}. Screens with tests: ${have.join(', ') || 'none yet'}.`);
  console.error(`Write ${DIR}/<Screen>.spec.ts after the screen's first passing drive-test.`);
  process.exit(2);
}

// A file filter is a regular expression over the path: anchor each one to its own file so
// "Customer" never also runs CustomerList.
const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const files = names.map((n) => `screens[\\\\/]${escape(n)}\\.spec\\.ts$`);
// --no-deprecation: a newer Node's warnings about Playwright's internals are noise here.
const nodeOptions = [process.env.NODE_OPTIONS, '--no-deprecation'].filter(Boolean).join(' ');
const env = { ...process.env, EVIDENCE_DIR: 'evidence/screens', SCREENS_RUN: '1', NODE_OPTIONS: nodeOptions };
// A pack that can't run is a setup problem, not a failing test: exit 2 with what to do, as
// for an unknown screen, so the build loop never reads it as a regression.
function cannotRun(why) {
  console.error(`Can't run the screen tests: ${why}. Run npm install && npm run setup in the pack.`);
  process.exit(2);
}
let cli;
try {
  cli = createRequire(import.meta.url).resolve('@playwright/test/cli');
} catch (error) {
  // Only a missing package means "not installed". Anything else (a Playwright release that
  // moved its ./cli export, a broken package.json) is named as it is, since reinstalling
  // the same version would not fix it.
  const missing = error?.code === 'MODULE_NOT_FOUND' && String(error.message).includes("'@playwright/test");
  if (missing) cannotRun('@playwright/test is not installed');
  console.error(`Can't run the screen tests: @playwright/test is installed but its CLI can't be loaded (${error?.code ?? 'error'}: ${String(error?.message ?? error).split('\n')[0]}).`);
  console.error('Check the @playwright/test version in package.json against the one the pack was scaffolded with.');
  process.exit(2);
}
const run = spawnSync(process.execPath, [cli, 'test', ...files, '--reporter', './scripts/compact-reporter.mjs'], {
  stdio: 'inherit',
  env,
});
if (run.error) cannotRun(run.error.message);
process.exit(run.status ?? 1);
