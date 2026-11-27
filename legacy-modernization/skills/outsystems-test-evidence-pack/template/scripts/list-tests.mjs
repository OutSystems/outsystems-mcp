// Lists every test and the tags Playwright resolves for it, without running anything,
// into evidence/tests.json. check_pack.py reads it, because tags built at runtime
// (req(v.id) in a loop) can't be read off the source.
//   npm run list

import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const cli = createRequire(import.meta.url).resolve('@playwright/test/cli');
const run = spawnSync(process.execPath, [cli, 'test', '--list', '--reporter=json'], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
if (run.status !== 0) {
  process.stderr.write(run.stderr || run.stdout);
  process.exit(run.status ?? 1);
}

const tests = [];
const walk = (suite) => {
  for (const s of suite.specs ?? []) tests.push({ title: s.title, file: s.file, line: s.line, tags: s.tags.map((t) => t.replace(/^@/, '')) });
  for (const child of suite.suites ?? []) walk(child);
};
for (const s of JSON.parse(run.stdout).suites) walk(s);

mkdirSync('evidence', { recursive: true });
writeFileSync('evidence/tests.json', JSON.stringify(tests, null, 2) + '\n');
console.log(`${tests.length} tests listed in evidence/tests.json`);
