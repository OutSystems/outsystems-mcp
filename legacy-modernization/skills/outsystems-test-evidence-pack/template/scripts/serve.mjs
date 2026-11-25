// Opens the traceability matrix in the browser with a working "Rerun tests" button, so the
// suite can be rerun from the page after a change to the app, and a Rerun button on each
// requirement that reruns only its tests.
//   npm start                 serves on http://127.0.0.1:4173 and opens the browser
//   npm start -- --no-open    serves without opening a browser
// The first rerun on a machine also sets the pack up: npm ci, the pinned Chromium, and a
// .env copied from .env.example. Uses only Node's own modules (it has to run before
// npm ci), listens on this machine only, and starts nothing but the pack's own run.

import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { copyFileSync, createReadStream, existsSync, readFileSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import path from 'node:path';

const root = path.resolve('evidence');
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.zip': 'application/zip',
  '.md': 'text/markdown; charset=utf-8', '.csv': 'text/csv; charset=utf-8', '.txt': 'text/plain; charset=utf-8',
};
// Handed only to a page this server served: a page on another site can't read it, so it
// can't start a run on this machine.
const token = randomBytes(16).toString('hex');

let run = null; // { log: string[], done: number, total: number, code: number|null, listeners: Set }

const setUp = () => existsSync('node_modules/@playwright/test');

function step(cmd, args) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [cmd, ...args], { env: process.env });
    for (const s of [child.stdout, child.stderr]) s.on('data', (b) => say(String(b)));
    child.on('close', (code) => resolve(code ?? 1));
    child.on('error', (e) => { say(String(e)); resolve(1); });
  });
}

function say(text) {
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    run.log.push(line);
    // The list reporter prints one line per finished test: ✓, ✘ or - (skipped), then its number.
    if (/^\s*(✓|✘|-|ok|x)\s+\d+\s/.test(line)) run.done++;
    send({ line, done: run.done, total: run.total });
  }
}

function send(event) {
  for (const res of run.listeners) res.write(`data: ${JSON.stringify(event)}\n\n`);
}

// ids: [] reruns everything into evidence/; a few requirement ids rerun just their tests into
// evidence/subset/ (scripts/run.mjs), so the full run's results stay as they were.
async function rerun(total, ids) {
  run = { log: [], done: 0, total, ids, code: null, listeners: run?.listeners ?? new Set() };
  let code = 0;
  if (!setUp()) {
    say('First run on this machine: installing the pack (npm ci) and its browser. This takes a few minutes.');
    // npm_execpath is set when this was started with npm start; the npm CLI is a Node script.
    const npm = process.env.npm_execpath;
    code = npm ? await step(npm, ['ci', '--no-audit', '--no-fund']) : (say('Run npm ci once in this folder, then try again.'), 1);
  }
  // Every run, not only the first: a browser download that failed (or a manual npm ci) is
  // retried here, and an installed browser makes this a quick check.
  if (code === 0) code = await step(path.join('node_modules', '@playwright', 'test', 'cli.js'), ['install', 'chromium']);
  if (code === 0 && !existsSync('.env') && existsSync('.env.example')) {
    copyFileSync('.env.example', '.env');
    say('Created .env from .env.example.');
  }
  if (code === 0) code = await step(path.join('scripts', 'run.mjs'), ids);
  run.code = code;
  send({ finished: true, code, ids });
}

const server = createServer((req, res) => {
  // Only this machine, by its loopback name: a page on another site that points a DNS name
  // at 127.0.0.1 gets nothing.
  const host = req.headers.host ?? '';
  if (!/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host)) return res.writeHead(403).end();
  let url;
  try {
    url = new URL(req.url, `http://${host}`);
  } catch {
    return res.writeHead(400).end('Bad request path.');
  }

  if (url.pathname === '/api/status') {
    res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
    return res.end(JSON.stringify({ token, setUp: setUp(), running: Boolean(run && run.code === null), ids: run?.ids ?? [] }));
  }
  if (url.pathname === '/api/run' && req.method === 'POST') {
    if (req.headers['x-pack-token'] !== token) return res.writeHead(403).end();
    if (run && run.code === null) return res.writeHead(409).end('A run is already going.');
    const total = Number(url.searchParams.get('total')) || 0;
    // Only ids requirements.json has: they become a test filter, nothing else.
    const ids = url.searchParams.getAll('id');
    if (ids.length) {
      let known;
      try {
        known = new Set(JSON.parse(readFileSync('requirements/requirements.json', 'utf8')).requirements.flatMap((r) => [r.id, ...(r.merged ?? [])]));
      } catch {
        return res.writeHead(500).end('requirements/requirements.json could not be read.');
      }
      if (ids.some((id) => !known.has(id))) return res.writeHead(400).end('Not a requirement id in requirements.json.');
    }
    rerun(total, ids);
    return res.writeHead(202).end();
  }
  if (url.pathname === '/api/events') {
    if (url.searchParams.get('token') !== token || !run) return res.writeHead(403).end();
    res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-store' });
    for (const line of run.log) res.write(`data: ${JSON.stringify({ line, done: run.done, total: run.total })}\n\n`);
    if (run.code !== null) res.write(`data: ${JSON.stringify({ finished: true, code: run.code, ids: run.ids })}\n\n`);
    run.listeners.add(res);
    req.on('close', () => run.listeners.delete(res));
    return;
  }

  let name;
  try {
    name = decodeURIComponent(url.pathname);
  } catch {
    return res.writeHead(400).end();
  }
  let file = path.join(root, name);
  if (file !== root && !file.startsWith(root + path.sep)) return res.writeHead(403).end();
  if (url.pathname === '/' || (existsSync(file) && statSync(file).isDirectory())) file = path.join(file, url.pathname === '/' ? 'traceability-matrix.html' : 'index.html');
  if (!existsSync(file)) {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    return res.end(run && run.code === null ? 'The tests are running; this page is rebuilt when they finish.' : 'Not found. Run the tests first: npm test');
  }
  res.writeHead(200, { 'content-type': TYPES[path.extname(file)] ?? 'application/octet-stream', 'cache-control': 'no-store' });
  createReadStream(file).pipe(res);
});

const port = Number(process.env.PORT) || 4173;
server.on('error', (e) => {
  console.error(e.code === 'EADDRINUSE' ? `Port ${port} is in use: close the other results window, or start with a different PORT.` : e.message);
  process.exit(1);
});
server.listen(port, '127.0.0.1', () => {
  const url = `http://127.0.0.1:${port}/`;
  console.log(`Test results: ${url}\nRerun the tests from that page. Press Ctrl+C here to stop.`);
  if (process.argv.includes('--no-open')) return;
  const [cmd, args] = process.platform === 'darwin' ? ['open', [url]]
    : process.platform === 'win32' ? ['explorer.exe', [url]]
    : ['xdg-open', [url]];
  spawn(cmd, args, { stdio: 'ignore', detached: true }).on('error', () => {}).unref();
});
