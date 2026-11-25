// Runs the suite, or only the tests for the requirements named on the command line,
// then builds the traceability matrix. Exits with the test run's status.
//   npm test                            the full run: evidence/
//   npm run test:req -- REQ-012         a few requirements: evidence/subset/, so the
//   npm run test:req -- REQ-010 BR-418  full run's report and matrix stay as they were
//   npm run test:req -- TEST-007        one test, by its own id (testId in tests/support.ts)
// Uses node directly (no shell), so it behaves the same in PowerShell, cmd and bash.

import { spawnSync } from 'node:child_process';
import { readFileSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';

const known = new Set(
  JSON.parse(readFileSync('requirements/requirements.json', 'utf8')).requirements.flatMap((r) => [r.id, ...(r.merged ?? [])]),
);
const ids = process.argv.slice(2);
// A test's own id (TEST-007) picks that one test; its tag is matched the same way.
const unknown = ids.filter((id) => !known.has(id) && !/^TEST-\d{3,}$/.test(id));
if (unknown.length) {
  console.error(`Not a requirement id in requirements/requirements.json, or a test id: ${unknown.join(', ')}`);
  console.error('Usage: npm run test:req -- REQ-012 [BR-418 TEST-007 ...]  (ids are case-sensitive)');
  process.exit(2);
}

const dir = ids.length ? 'evidence/subset' : 'evidence';
const env = { ...process.env, EVIDENCE_DIR: dir, SUBSET_IDS: ids.join(' ') };
// A run that dies before writing results must leave no matrix, never the last run's or one
// rebuilt from the last run's results. The HTML report is replaced by the run itself.
for (const f of ['results.json', 'summary.json', 'traceability-matrix.html', 'traceability-matrix.md', 'traceability-matrix.csv']) {
  rmSync(`${dir}/${f}`, { force: true });
}

// A tag ends where the id does, so REQ-001 doesn't also pick up REQ-001-V2.
const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const cli = createRequire(import.meta.url).resolve('@playwright/test/cli');
const grep = ids.length ? ['--grep', ids.map((id) => `@${escape(id)}(?![\\w.-])`).join('|')] : [];
const run = spawnSync(process.execPath, [cli, 'test', ...grep], { stdio: 'inherit', env });
const matrix = spawnSync(process.execPath, ['scripts/build-matrix.mjs'], { stdio: 'inherit', env });
// Green tests with no matrix is no evidence: a failed or crashed matrix build fails the run too.
const code = run.status ?? 1;
process.exit(code !== 0 ? code : (matrix.status ?? 1));
