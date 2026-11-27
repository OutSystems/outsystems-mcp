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

// Every id, canonical or merged, maps to its requirement's whole id group: a test is
// tagged with the canonical id, so asking for a merged id must select it too.
const groups = new Map();
for (const r of JSON.parse(readFileSync('requirements/requirements.json', 'utf8')).requirements) {
  const group = [r.id, ...(r.merged ?? [])];
  for (const id of group) groups.set(id, group);
}
const known = new Set(groups.keys());
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
// A test id (TEST-007) has no group: it is its own tag.
const tags = [...new Set(ids.flatMap((id) => groups.get(id) ?? [id]))];
const grep = ids.length ? ['--grep', tags.map((id) => `@${escape(id)}(?![\\w.-])`).join('|')] : [];
const run = spawnSync(process.execPath, [cli, 'test', ...grep], { stdio: 'inherit', env });
const matrix = spawnSync(process.execPath, ['scripts/build-matrix.mjs'], { stdio: 'inherit', env });
// Green tests with no matrix is no evidence: a failed or crashed matrix build fails the run too.
const code = run.status ?? 1;
if (code !== 0) process.exit(code);
if (matrix.status !== 0) process.exit(matrix.status ?? 1);
// Playwright exits 0 for a test.fail() test whose body failed; the matrix counts it as a
// failure, so the run exits as the matrix reads.
const failed = JSON.parse(readFileSync(`${dir}/summary.json`, 'utf8')).tests?.failed ?? 0;
if (failed) {
  console.error(`${failed} test(s) failed (a test.fail() test whose body failed counts): see ${dir}/traceability-matrix.html`);
  process.exit(1);
}
