// Zips the pack for handover: the tests, the requirements, and the last full run's matrix,
// report and traces, so the customer can read the evidence before installing anything and
// re-run the tests after `npm ci`. Writes dist/<name>.zip.
//   npm run handover
// Leaves out what is local or rebuilt: node_modules, .env, the raw test artifacts (the
// report already holds every trace and screenshot), any subset run and the build's
// screen-test runs (evidence/screens).
// Uses only Node's own modules, so it behaves the same on macOS, Windows and Linux.

import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { deflateRawSync } from 'node:zlib';

const name = JSON.parse(readFileSync('package.json', 'utf8')).name;
const SKIP = new Set(['node_modules', '.env', '.git', 'dist', 'test-results', 'evidence/artifacts', 'evidence/subset', 'evidence/screens']);

for (const f of ['evidence/summary.json', 'evidence/traceability-matrix.html', 'evidence/html-report/index.html']) {
  if (!existsSync(f)) {
    console.error(`Missing ${f}. Run the full suite first (npm test), so the pack ships with its evidence.`);
    process.exit(1);
  }
}

const files = [];
const walk = (dir) => {
  for (const entry of readdirSync(dir || '.', { withFileTypes: true })) {
    const rel = dir ? `${dir}/${entry.name}` : entry.name;
    if (SKIP.has(rel)) continue;
    if (entry.isDirectory()) walk(rel);
    else if (entry.isFile()) files.push(rel);
  }
};
walk('');
files.sort();

const CRC = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
const crc32 = (buf) => {
  let c = 0xffffffff;
  for (const b of buf) c = CRC[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};
const dosTime = (d) => ({
  time: (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
  date: ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate(),
});

// A plain zip (deflate, UTF-8 names), which Explorer, Finder and unzip all open.
const parts = [];
const central = [];
let offset = 0;
// The run's JSON records where the pack sat on this machine (and so the user's name):
// the zip carries those paths relative to the pack instead.
const here = JSON.stringify(process.cwd()).slice(1, -1);
const local = (rel) => /^evidence\/[^/]+\.json$/.test(rel);
for (const rel of files) {
  const raw = readFileSync(rel);
  const data = local(rel) ? Buffer.from(raw.toString('utf8').split(here).join('.')) : raw;
  const packed = deflateRawSync(data);
  // Traces, screenshots and other zips are already compressed: store them when deflate doesn't help.
  const [method, body] = packed.length < data.length ? [8, packed] : [0, data];
  const name = Buffer.from(rel, 'utf8');
  const { time, date } = dosTime(statSync(rel).mtime);
  const crc = crc32(data);
  const head = Buffer.alloc(30);
  head.writeUInt32LE(0x04034b50, 0);
  head.writeUInt16LE(20, 4);
  head.writeUInt16LE(0x0800, 6);
  head.writeUInt16LE(method, 8);
  head.writeUInt16LE(time, 10);
  head.writeUInt16LE(date, 12);
  head.writeUInt32LE(crc, 14);
  head.writeUInt32LE(body.length, 18);
  head.writeUInt32LE(data.length, 22);
  head.writeUInt16LE(name.length, 26);
  parts.push(head, name, body);
  const entry = Buffer.alloc(46);
  entry.writeUInt32LE(0x02014b50, 0);
  entry.writeUInt16LE(20, 4);
  entry.writeUInt16LE(20, 6);
  entry.writeUInt16LE(0x0800, 8);
  entry.writeUInt16LE(method, 10);
  entry.writeUInt16LE(time, 12);
  entry.writeUInt16LE(date, 14);
  entry.writeUInt32LE(crc, 16);
  entry.writeUInt32LE(body.length, 20);
  entry.writeUInt32LE(data.length, 24);
  entry.writeUInt16LE(name.length, 28);
  entry.writeUInt32LE(offset, 42);
  central.push(entry, name);
  offset += head.length + name.length + body.length;
}
const dir = Buffer.concat(central);
const end = Buffer.alloc(22);
end.writeUInt32LE(0x06054b50, 0);
end.writeUInt16LE(files.length, 8);
end.writeUInt16LE(files.length, 10);
end.writeUInt32LE(dir.length, 12);
end.writeUInt32LE(offset, 16);

const out = path.join('dist', `${name}.zip`);
mkdirSync('dist', { recursive: true });
const zip = Buffer.concat([...parts, dir, end]);
writeFileSync(out, zip);
console.log(`Wrote ${out}: ${files.length} files, ${(zip.length / 1048576).toFixed(1)} MB.`);
