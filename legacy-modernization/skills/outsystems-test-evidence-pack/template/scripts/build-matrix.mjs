// Builds the requirement traceability matrix from requirements.json and the Playwright
// JSON results: requirement -> where it lives in the app -> tests -> result -> evidence.
// Writes evidence/traceability-matrix.{html,md,csv} and evidence/summary.json. Plain Node,
// no shell, so it runs the same on macOS, Windows and Linux.
//
// requirements.json is the coverage denominator: every requirement gets a row, so one no
// test is tagged with shows as Not covered instead of going missing. Its ids are the
// extractor's, unchanged; a test tagged with an id the file doesn't have is listed apart.
// Each test also carries its own id (`testId('TEST-007')`, a TEST- tag), which every output
// names it by, so the Implementation Report can cite a test that survives a reworded title.

import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// .env, read by Node itself (20.12+), so the matrix builds with nothing installed.
try {
  process.loadEnvFile(path.join(root, '.env'));
} catch {
  // No .env: the matrix just doesn't name the app URL.
}
// A run of a few requirements (scripts/run.mjs) writes to evidence/subset and lists only those.
const out = path.join(root, process.env.EVIDENCE_DIR ?? 'evidence');
const subset = (process.env.SUBSET_IDS ?? '').split(' ').filter(Boolean);
const resultsFile = path.join(out, 'results.json');
if (!existsSync(resultsFile)) {
  console.error(`No ${path.relative(root, resultsFile)}: the run wrote no results, so there is no matrix. Run "npm test".`);
  process.exit(1);
}

const spec = JSON.parse(readFileSync(path.join(root, 'requirements', 'requirements.json'), 'utf8'));
const results = JSON.parse(readFileSync(resultsFile, 'utf8'));
// The same default playwright.config.ts falls back to, so the matrix names the app the run tested.
const baseUrl = (process.env.APP_BASE_URL || '{{BASE_URL}}').replace(/\/$/, '');
// The app revision the run tested, so a verdict names the build it is about (APP_REVISION in .env).
const revision = (process.env.APP_REVISION ?? '').trim();

// A test's own id, as tests/support.ts's testId() writes it. Never a requirement id.
const TEST_ID = /^TEST-\d{3,}$/;

// Flatten every test the run produced, keeping the tags that link it to requirements.
const tests = [];
const walk = (suite, titles) => {
  for (const s of suite.specs ?? []) {
    for (const t of s.tests) {
      const last = t.results.at(-1) ?? { status: 'skipped' };
      // A flaky test's last result is the retry that passed: show the try that failed.
      const shown = t.status === 'flaky' ? t.results.findLast((r) => r.status !== 'passed') ?? last : last;
      // A skip declared on the test is in t.annotations; test.skip(condition, reason) at run time is on the result.
      const skipReason = [...(t.annotations ?? []), ...(last.annotations ?? [])].find((a) => a.type === 'skip')?.description ?? '';
      const tags = s.tags.map((tag) => tag.replace(/^@/, ''));
      tests.push({
        id: s.id,
        // The test's own id (TEST-007); '' for a test check_pack.py would refuse.
        testId: tags.find((tag) => TEST_ID.test(tag)) ?? '',
        title: [...titles, s.title].filter(Boolean).join(' › '),
        file: `${s.file}:${s.line}`,
        tags,
        // Flaky (failed, then passed on retry) is its own result, never a pass.
        status: t.status === 'flaky' ? 'flaky' : last.status === 'skipped' ? 'skipped' : t.status === 'expected' ? 'passed' : 'failed',
        error: firstLine(shown.errors?.[0]?.message ?? shown.error?.message ?? ''),
        skipReason,
        attachments: (last.attachments ?? []).filter((a) => a.name !== 'trace').length,
        ranAt: last.startTime ?? '',
        // The Given / When / Then steps as the run reported them, the failing one marked.
        steps: (shown.steps ?? []).map((st) => ({ title: st.title, failed: Boolean(st.error) })),
        // Playwright's own screenshot of a failed test, copied below to a folder that ships.
        screenshot: (shown.attachments ?? []).find((a) => a.name === 'screenshot' && a.path)?.path ?? '',
      });
    }
  }
  for (const child of suite.suites ?? []) walk(child, [...titles, child.title.endsWith('.ts') ? '' : child.title]);
};
for (const s of results.suites) walk(s, []);

// The raw artifacts stay out of the handover zip, so each failure screenshot the matrix shows
// is copied to evidence/screenshots/<test id>.png, which ships with it.
const shots = path.join(out, 'screenshots');
rmSync(shots, { recursive: true, force: true });
for (const t of tests) {
  if (!t.screenshot || t.status === 'passed' || !existsSync(t.screenshot)) {
    t.screenshot = '';
    continue;
  }
  mkdirSync(shots, { recursive: true });
  const copy = path.join(shots, `${t.id.replace(/[^\w-]/g, '_')}.png`);
  copyFileSync(t.screenshot, copy);
  t.screenshot = copy;
}

function firstLine(msg) {
  return msg.replace(/\x1b\[[0-9;]*m/g, '').split('\n').find((l) => l.trim() && !l.startsWith('expect('))?.replace(/^Error:\s*/, '').trim() ?? '';
}

const verdict = (r, ts) => {
  if (ts.length === 0) return r.untestable ? 'Blocked' : 'Not covered';
  if (ts.some((t) => t.status === 'failed')) return 'Fail';
  if (ts.some((t) => t.status === 'flaky')) return 'Flaky';
  if (ts.some((t) => t.status === 'passed')) return ts.some((t) => t.status === 'skipped') ? 'Pass (partial)' : 'Pass';
  return 'Blocked';
};

// A test as the outputs name it: its own id first, when it has one.
const named = (t) => (t.testId ? `${t.testId} ${t.title}` : t.title);

// An id folded into another entry (`merged`) counts for that entry. A subset run of one test
// (npm run test:req -- TEST-007) lists the requirements that test proves.
const inSubset = (r) => {
  const ids = [r.id, ...(r.merged ?? [])];
  return ids.some((id) => subset.includes(id)) || tests.some((t) => subset.includes(t.testId) && t.tags.some((tag) => ids.includes(tag)));
};
const listed = subset.length ? spec.requirements.filter(inSubset) : spec.requirements;
const rows = listed.map((r) => {
  const ids = [r.id, ...(r.merged ?? [])];
  const ts = tests.filter((t) => t.tags.some((tag) => ids.includes(tag)));
  const where = (r.screens ?? []).map((id) => {
    const s = spec.screens?.[id];
    return s ? { id, name: s.name, route: s.route } : { id, name: id, route: null };
  });
  return { ...r, group: r.group ?? r.tier ?? '', where, tests: ts, verdict: verdict(r, ts), why: r.untestable ?? '', cite: citation(r) };
});

// Where the requirement comes from in the legacy source (file, form, line), as the extraction cites it.
// One line, so it fits a table cell; an object citation ({ file, form, line }) reads as its values.
function citation(r) {
  const flat = (v) => (v && typeof v === 'object' ? Object.values(v).map(flat).filter(Boolean).join(', ') : String(v ?? ''));
  return flat(r.source || r.derived_from?.source).replace(/`/g, '').replace(/\s+/g, ' ').trim();
}
const known = new Set(spec.requirements.flatMap((r) => [r.id, ...(r.merged ?? [])]));
const other = tests.filter((t) => !t.tags.some((tag) => known.has(tag)));
const strayTags = [...new Set(tests.flatMap((t) => t.tags).filter((tag) => !known.has(tag) && !TEST_ID.test(tag) && /\d/.test(tag)))];
// check_pack.py refuses both; the matrix still builds, and says so.
const unnamed = tests.filter((t) => !t.testId);
const reused = [...new Set(tests.map((t) => t.testId).filter((id, i, all) => id && all.indexOf(id) !== i))];

const tally = (rs) => {
  const count = (v) => rs.filter((r) => r.verdict === v).length;
  return {
    total: rs.length,
    pass: count('Pass') + count('Pass (partial)'),
    fail: count('Fail'),
    flaky: count('Flaky'),
    blocked: count('Blocked'),
    notCovered: count('Not covered'),
  };
};
const summary = tally(rows);
// Coverage per tier (functional, business, ...), so a few hundred business rules don't hide
// how the functional requirements did.
const tiers = [...new Set(rows.map((r) => r.tier).filter(Boolean))];
const byTier = Object.fromEntries(tiers.map((tier) => [tier, tally(rows.filter((r) => r.tier === tier))]));
const tierLine = (t, s) => `${t}: ${s.pass} pass, ${s.fail} fail, ${s.flaky} flaky, ${s.blocked} blocked, ${s.notCovered} not covered (of ${s.total})`;
const scope = subset.length ? `Subset run (${subset.join(', ')}); the full matrix is in evidence/. ` : '';
const runAt = new Date(results.stats.startTime);

// A screen route with exactly one leading slash, however requirements.json spells it.
const route = (r) => `/${String(r).replace(/^\//, '')}`;

// ---------- CSV ----------
const csvCell = (v) => `"${String(v).replace(/"/g, '""')}"`;
const csv = [
  ['Requirement', 'Group', 'Requirement text', 'Source', 'Where in the app', 'Tests', 'Result', 'Failure or skip reason'],
  ...rows.map((r) => [
    r.id,
    r.group,
    r.text,
    r.cite,
    r.where.map((w) => `${w.id} ${w.name}${w.route ? ` (${route(w.route)})` : ' (not built)'}`).join('; '),
    r.tests.map((t) => `${named(t)} [${t.status}]`).join('; '),
    r.verdict,
    [r.why, ...r.tests.map((t) => t.error || t.skipReason)].filter(Boolean).join('; '),
  ]),
].map((line) => line.map(csvCell).join(',')).join('\r\n');
writeFileSync(path.join(out, 'traceability-matrix.csv'), csv + '\r\n');

// ---------- Markdown ----------
const md = [
  `# Traceability matrix: ${spec.app}`,
  '',
  `${scope}Run ${runAt.toISOString()} against ${baseUrl || '(APP_BASE_URL)'}${revision ? `, revision ${revision}` : ''}. Requirements: ${spec.source}.`,
  '',
  `**${summary.pass} pass · ${summary.fail} fail · ${summary.flaky} flaky · ${summary.blocked} blocked · ${summary.notCovered} not covered** (of ${summary.total} requirements)`,
  '',
  ...Object.entries(byTier).map(([t, s]) => `- ${tierLine(t, s)}`),
  ...(tiers.length ? [''] : []),
  '| Requirement | Source | Where in the app | Tests | Result | Why |',
  '|---|---|---|---|---|---|',
  ...rows.map((r) =>
    [
      `**${r.id}** ${r.text.replace(/\s+/g, ' ').replace(/\|/g, '\\|')}`,
      r.cite ? `\`${r.cite.replace(/\|/g, '\\|')}\`` : '—',
      r.where.map((w) => `${w.id} ${w.route ? `\`${route(w.route)}\`` : '*not built*'}`).join('<br>') || '—',
      r.tests.map((t) => `${t.testId ? `\`${t.testId}\` ` : ''}${t.title.replace(/\|/g, '\\|')} (${t.status})`).join('<br>') || '—',
      r.verdict,
      [r.why, ...r.tests.map((t) => t.error || t.skipReason)].filter(Boolean).map((w) => w.replace(/\|/g, '\\|')).join('<br>'),
    ].join(' | '),
  ).map((l) => `| ${l} |`),
  '',
  '## Other checks (not tagged with a requirement)',
  '',
  ...other.map((t) => `- ${named(t)}: **${t.status}**${t.error || t.skipReason ? ` — ${t.error || t.skipReason}` : ''}`),
  ...(strayTags.length ? ['', `Tagged with ids requirements.json doesn't have: ${strayTags.join(', ')}`] : []),
  '',
].join('\n');
writeFileSync(path.join(out, 'traceability-matrix.md'), md);

// ---------- HTML ----------
// Laid out like the generator's Tests tab: the pass rate and a bar on top, then one row per
// requirement under its section, each opening to its tests as Given / When / Then scenarios.
// Works with no script (rows open natively); the script adds the chip filter and local times.
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const rel = (p) => path.relative(out, p).split(path.sep).join('/');
const shownTime = (iso) => (iso ? `<time datetime="${esc(iso)}">${esc(new Date(iso).toUTCString().slice(5, 22))} UTC</time>` : '');

const ICON = {
  pass: '<path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><path d="m9 11 3 3L22 4"/>',
  fail: '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
  flaky: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><path d="M12 9v4M12 17h.01"/>',
  blocked: '<circle cx="12" cy="12" r="10"/><path d="M8 12h8"/>',
  none: '<path d="M10.1 2.2a10 10 0 0 1 3.8 0M17.6 3.7a10 10 0 0 1 2.7 2.7M21.8 10.1a10 10 0 0 1 0 3.8M20.3 17.6a10 10 0 0 1-2.7 2.7M13.9 21.8a10 10 0 0 1-3.8 0M6.4 20.3a10 10 0 0 1-2.7-2.7M2.2 13.9a10 10 0 0 1 0-3.8M3.7 6.4a10 10 0 0 1 2.7-2.7"/>',
  chevron: '<path d="m9 18 6-6-6-6"/>',
};
const icon = (name, cls = name) =>
  `<svg class="ic ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[name]}</svg>`;
const KIND = { Pass: 'pass', 'Pass (partial)': 'pass', Fail: 'fail', Flaky: 'flaky', Blocked: 'blocked', 'Not covered': 'none' };
const TEST_KIND = { passed: 'pass', failed: 'fail', flaky: 'flaky', skipped: 'blocked' };
const TEST_WORD = { passed: 'PASS', failed: 'FAIL', flaky: 'FLAKY', skipped: 'SKIPPED' };
const chip = (label, kind) => `<button type="button" class="chip ${kind}" data-chip="${esc(label)}" title="Show only ${esc(label)}">${esc(label)}</button>`;

// "Given a visitor ..." -> keyword and text; a repeat of the same keyword reads "And".
const scenario = (t) => {
  let last = '';
  const lines = t.steps.map((st) => {
    const m = st.title.match(/^(Given|When|Then|And)\s+(.*)$/s);
    const word = m ? (m[1] === last || m[1] === 'And' ? 'And' : m[1]) : '';
    if (m && m[1] !== 'And') last = m[1];
    return `<div class="step${st.failed ? ' failed' : ''}"><b>${esc(word)}</b> ${esc(m ? m[2] : st.title)}</div>`;
  });
  return `<div class="gherkin"><div><b>Scenario:</b> ${esc(t.title)}</div>${lines.join('')}</div>`;
};

const testBlock = (t) => `<div class="test">
<div class="test-head">${icon(TEST_KIND[t.status], TEST_KIND[t.status])}${t.testId ? `<code class="tid">${esc(t.testId)}</code>` : ''}<a href="html-report/index.html#?testId=${encodeURIComponent(t.id)}" title="Open its trace and screenshots">${esc(t.title)}</a>
<span class="when">${TEST_WORD[t.status]}${t.ranAt ? ` · ${shownTime(t.ranAt)}` : ''}</span></div>
${t.error ? `<div class="failure">${esc(t.error)}</div>` : ''}${t.skipReason ? `<div class="reason">${esc(t.skipReason)}</div>` : ''}
${t.steps.length ? scenario(t) : ''}
${t.screenshot && t.status !== 'passed' ? `<a class="shot" href="${esc(rel(t.screenshot))}" target="_blank" rel="noreferrer" title="Open the full screenshot"><img src="${esc(rel(t.screenshot))}" alt="${esc(t.title)} when it failed" loading="lazy"></a>` : ''}
</div>`;

// Failing tests first: they are the reason to open the row.
const CONCERN = { failed: 0, flaky: 1, skipped: 2, passed: 3 };
const byConcern = (ts) => [...ts].sort((x, y) => CONCERN[x.status] - CONCERN[y.status]);

const rowFor = (r) => {
  const kind = KIND[r.verdict];
  const ranAt = r.tests.map((t) => t.ranAt).filter(Boolean).sort().at(-1);
  // Screens, then any tag that isn't a requirement id (ACCESS), as the Tests tab shows them.
  const plainTags = [...new Set(r.tests.flatMap((t) => t.tags).filter((tag) => !known.has(tag) && !TEST_ID.test(tag)))];
  const chips = [...r.where.map((w) => chip(w.name, 'screen')), ...plainTags.map((tag) => chip(tag, 'tag'))];
  const filterBy = [r.id, ...(r.merged ?? []), ...r.where.map((w) => w.name), ...r.tests.flatMap((t) => t.tags)];
  return `<li class="row" id="req-${esc(r.id)}" data-id="${esc(r.id)}" data-kind="${kind}" data-chips="${esc(JSON.stringify(filterBy))}"><details${kind === 'fail' || kind === 'flaky' ? ' open' : ''}>
<summary>${icon('chevron', 'chev')}${icon(kind)}<span class="name"><b>${esc(r.id)}</b> ${esc(r.text)}</span><span class="chips">${chips.join('')}</span>
<span class="again" hidden></span><span class="when">${esc(r.verdict.toUpperCase())}${ranAt ? ` · ${shownTime(ranAt)}` : ''}</span></summary>
<div class="body">
<p class="text">${esc(r.text)}</p>
${r.cite ? `<p class="where">Source: <code>${esc(r.cite)}</code></p>` : ''}
${r.where.length ? `<p class="where">${r.where.map((w) => `${esc(w.name)} ${w.route ? `<code>${esc(route(w.route))}</code>` : '<em>not built</em>'}`).join(' · ')}</p>` : ''}
${r.why ? `<div class="reason">${esc(r.why)}</div>` : ''}
${r.tests.length ? byConcern(r.tests).map(testBlock).join('') : r.why ? '' : '<div class="reason">No test is tagged with this requirement yet.</div>'}
${r.tests.length && !subset.length ? `<div class="row-actions" hidden><button type="button" class="rerun-one" data-rerun="${esc(r.id)}" data-total="${r.tests.length}">Rerun ${esc(r.id)}</button><span class="rerun-result"></span></div>` : ''}
</div></details></li>`;
};

// Sections as the Implementation Report heads them: one per tier, a subsection per group.
const TIER_TITLE = { functional: 'Functional requirements', business: 'Business rules' };
const sectionTitle = (tier) => TIER_TITLE[tier] ?? (tier ? tier[0].toUpperCase() + tier.slice(1) : 'Requirements');
// Functional first, as the report orders them; any other tier after, in file order.
const sectionOrder = [...new Set(rows.map((r) => r.tier ?? ''))].sort((a, b) => (b === 'functional') - (a === 'functional'));
const sections = sectionOrder.map((tier, i) => {
  const inTier = rows.filter((r) => (r.tier ?? '') === tier);
  const groups = [...new Set(inTier.map((r) => r.group && r.group !== tier ? r.group : ''))];
  const body = groups
    .map((g, j) => {
      const list = `<ul>${inTier.filter((r) => (r.group && r.group !== tier ? r.group : '') === g).map(rowFor).join('\n')}</ul>`;
      return g ? `<h4>${i + 1}.${j + 1} ${esc(g)}</h4>${list}` : list;
    })
    .join('');
  const s = byTier[tier];
  return `<section><h3>${i + 1}. ${esc(sectionTitle(tier))}${s ? ` <span>${s.pass} of ${s.total} pass</span>` : ''}</h3>${body}</section>`;
});
if (other.length)
  sections.push(
    `<section><h3>${sections.length + 1}. Other checks <span>not tagged with a requirement</span></h3><div class="others">${other.map(testBlock).join('')}</div></section>`,
  );

// The summary table: one line per section (and per group within it), how many requirements
// and tests passed, and a total over every test (the untagged ones too). It is the whole
// run, whatever the filter shows.
const testsOf = (rs) => [...new Set(rs.flatMap((r) => r.tests))];
const tableRow = (label, rs, cls = '', ts = testsOf(rs)) => {
  const s = tally(rs);
  const cell = (n, kind) => `<td class="n${n ? ' ' + kind : ''}">${n}</td>`;
  return `<tr${cls ? ` class="${cls}"` : ''}><th scope="row">${esc(label)}</th><td class="n">${s.total}</td>${cell(s.pass, 'pass')}${cell(s.fail, 'fail')}${cell(s.flaky + s.blocked, 'warn')}${cell(s.notCovered, 'none')}<td class="n">${ts.filter((t) => t.status === 'passed').length} of ${ts.length}</td></tr>`;
};
const tableRows = sectionOrder.flatMap((tier) => {
  const inTier = rows.filter((r) => (r.tier ?? '') === tier);
  const groups = [...new Set(inTier.map((r) => (r.group && r.group !== tier ? r.group : '')))].filter(Boolean);
  return [
    tableRow(sectionTitle(tier), inTier, groups.length ? 'tier' : ''),
    ...groups.map((g) => tableRow(g, inTier.filter((r) => r.group === g), 'group')),
  ];
});
const summaryTable = `<div class="table-wrap"><table class="summary">
<thead><tr><th scope="col">Area</th><th scope="col" class="n">Requirements</th><th scope="col" class="n">Passed</th><th scope="col" class="n">Failed</th><th scope="col" class="n">Flaky or blocked</th><th scope="col" class="n">Not covered</th><th scope="col" class="n">Tests passed</th></tr></thead>
<tbody>${tableRows.join('')}</tbody>
<tfoot>${tableRow('Total', rows, '', tests)}</tfoot>
</table></div>`;

const pct = (n) => (summary.total ? (100 * n) / summary.total : 0);
const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Traceability Matrix</title>
<style>
:root{--bg:#f8fafc;--surface:#fff;--ink:#1e293b;--ink2:#334155;--muted:#64748b;--faint:#94a3b8;--line:#e2e8f0;--soft:#f1f5f9;--hover:#f8fafc;
--accent:#4f46e5;--accent-ink:#4338ca;--accent-bg:#eef2ff;--pass:#10b981;--pass-bar:#34d399;--pass-ink:#047857;--pass-bg:#ecfdf5;--fail:#f43f5e;--fail-bar:#fb7185;--fail-ink:#be123c;--fail-bg:#fff1f2;--fail-chip:#ffe4e6;
--warn:#d97706;--warn-bar:#fbbf24;--warn-ink:#b45309;--warn-bg:#fffbeb;--teal-ink:#0f766e;--teal-bg:#f0fdfa;--kw:#7c3aed}
@media (prefers-color-scheme:dark){:root{--bg:#0f172a;--surface:#111827;--ink:#f1f5f9;--ink2:#cbd5e1;--muted:#94a3b8;--faint:#64748b;--line:#1f2937;--soft:#1e293b;--hover:#172033;
--accent:#6366f1;--accent-ink:#a5b4fc;--accent-bg:#1e1b4b;--pass:#34d399;--pass-bar:#10b981;--pass-ink:#6ee7b7;--pass-bg:#022c22;--fail:#fb7185;--fail-bar:#f43f5e;--fail-ink:#fda4af;--fail-bg:#3b0d17;--fail-chip:#4c0519;
--warn:#fbbf24;--warn-bar:#d97706;--warn-ink:#fcd34d;--warn-bg:#3a2a07;--teal-ink:#5eead4;--teal-bg:#042f2e;--kw:#c4b5fd}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 ui-sans-serif,system-ui,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:15px;font-weight:600;margin:0}.meta{color:var(--muted);font-size:12px;margin:2px 0 18px;overflow-wrap:anywhere}
.top{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.pct{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums}
.of{font-size:12px;color:var(--muted);line-height:1.25}.of b{display:block;color:var(--ink2);font-weight:500}
.open{margin-left:auto;display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:6px;background:var(--accent);color:#fff;font-size:12px;font-weight:500;text-decoration:none}
.open:hover{filter:brightness(.92)}
.bar{display:flex;height:6px;border-radius:99px;background:var(--soft);overflow:hidden;margin:10px 0 8px}.bar i{display:block;height:100%}
.bar .pass{background:var(--pass-bar)}.bar .fail{background:var(--fail-bar)}.bar .warn{background:var(--warn-bar)}
.counts{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:12px}.counts .last{margin-left:auto;color:var(--faint)}
.count{font:500 11px/1.4 inherit;border:0;border-radius:4px;padding:1px 6px;cursor:pointer}.count:hover{filter:brightness(.95)}.count[aria-pressed=true]{box-shadow:0 0 0 1.5px currentColor}.count.pass{color:var(--pass-ink);background:var(--pass-bg)}.count.fail{color:var(--fail-ink);background:var(--fail-chip)}.count.warn{color:var(--warn-ink);background:var(--warn-bg)}.count.none{color:var(--ink2);background:var(--soft)}
.rerun{font-size:12px;color:var(--muted);margin:10px 0 0}.rerun code{color:var(--ink2);background:var(--soft);border-radius:4px;padding:1px 5px}
.open.ghost{margin-left:auto;background:var(--surface);color:var(--accent-ink);border:1px solid var(--line);cursor:pointer;font-family:inherit}.open.ghost+.open{margin-left:0}.open.ghost:disabled{opacity:.6;cursor:default}
.progress{margin-top:12px;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px}.progress-head{display:flex;gap:8px;align-items:baseline;font-size:13px}.progress-head span{margin-left:auto;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.progress pre{margin:8px 0 0;max-height:140px;overflow:auto;font:11px/1.6 ui-monospace,Menlo,Consolas,monospace;color:var(--muted);white-space:pre-wrap;overflow-wrap:anywhere}
.table-wrap{margin-top:14px;overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:8px}
.summary{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
.summary th,.summary td{padding:7px 12px;text-align:left;border-bottom:1px solid var(--soft);white-space:nowrap}
.summary thead th{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.summary tbody th{font-weight:500;color:var(--ink2)}.summary tr.group th{padding-left:28px;font-weight:400;color:var(--muted)}
.summary .n{text-align:right}.summary td.pass{color:var(--pass-ink)}.summary td.fail{color:var(--fail-ink);font-weight:600}.summary td.warn{color:var(--warn-ink)}.summary td.none{color:var(--muted)}
.summary tfoot th,.summary tfoot td{border-bottom:0;font-weight:600;color:var(--ink)}.summary tfoot tr{background:var(--soft)}
.row-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;border-top:1px dashed var(--line);padding-top:10px;font-size:12px;color:var(--muted)}
.rerun-one{font:500 12px/1 inherit;color:var(--accent-ink);background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:6px 10px;cursor:pointer}.rerun-one:disabled{opacity:.6;cursor:default}
.rerun-result a{color:var(--accent-ink)}.again{font-size:10px;font-weight:600;border-radius:4px;padding:1px 6px;white-space:nowrap;flex:none}
.again.pass{color:var(--pass-ink);background:var(--pass-bg)}.again.fail{color:var(--fail-ink);background:var(--fail-chip)}.again.warn{color:var(--warn-ink);background:var(--warn-bg)}.again.none{color:var(--ink2);background:var(--soft)}
.filter{display:none;align-items:center;gap:4px;font:500 11px/1 inherit;color:var(--accent-ink);background:var(--accent-bg);border:0;border-radius:4px;padding:3px 6px;cursor:pointer}.filter.on{display:inline-flex}
section{margin-top:22px}h3{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);margin:0 0 6px}
h3 span{font-weight:400;text-transform:none;letter-spacing:0;color:var(--faint);margin-left:4px}h4{font-size:11px;font-weight:500;color:var(--muted);margin:10px 0 6px 8px}
ul{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:minmax(0,1fr);gap:6px}
.row{background:var(--surface);border:1px solid var(--line);border-radius:8px}.row.hidden{display:none}
summary{display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;list-style:none;border-radius:8px}summary::-webkit-details-marker{display:none}summary:hover{background:var(--hover)}
.ic{width:16px;height:16px;flex:none}.ic.chev{width:14px;height:14px;color:var(--faint);transition:transform .15s}details[open] .chev{transform:rotate(90deg)}
.ic.pass{color:var(--pass)}.ic.fail{color:var(--fail)}.ic.flaky{color:var(--warn)}.ic.blocked{color:var(--warn)}.ic.none{color:var(--faint)}
.name{font-size:14px;font-weight:500;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1 1 0}.name b{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;font-weight:600;margin-right:2px}
.chips{display:flex;gap:4px;flex:none}
.chip{font:10px/1.4 inherit;border:0;border-radius:4px;padding:2px 6px;cursor:pointer;white-space:nowrap}.chip.screen{color:var(--ink2);background:var(--soft)}.chip.id{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--accent-ink);background:var(--accent-bg)}.chip.tag{color:var(--teal-ink);background:var(--teal-bg)}
.chip:hover{filter:brightness(.95)}.when{font-size:11px;color:var(--faint);white-space:nowrap;font-variant-numeric:tabular-nums;flex:none}
.body{border-top:1px solid var(--soft);padding:10px 12px 12px;display:grid;grid-template-columns:minmax(0,1fr);gap:8px}.text{margin:0;color:var(--ink2)}.where{margin:0;font-size:12px;color:var(--muted)}
code{font:12px ui-monospace,Menlo,Consolas,monospace}
.test{display:grid;gap:6px}.test+.test{border-top:1px dashed var(--line);padding-top:10px}.test-head{display:flex;align-items:center;gap:8px;font-size:13px}.test-head a{color:var(--ink);font-weight:500;text-decoration:none}.test-head a:hover{text-decoration:underline}
.failure{font-size:12px;color:var(--fail-ink);background:var(--fail-bg);border-radius:4px;padding:6px 8px;overflow-wrap:anywhere}
.reason{font-size:12px;color:var(--warn-ink);background:var(--warn-bg);border-radius:4px;padding:6px 8px}
.gherkin{background:var(--soft);border-radius:4px;padding:8px 10px;font:11px/1.7 ui-monospace,Menlo,Consolas,monospace;color:var(--ink2);overflow-wrap:anywhere}
.gherkin b{color:var(--kw);font-weight:600}.gherkin .step{padding-left:12px}.gherkin .step.failed{color:var(--fail-ink)}
.shot{display:block;max-height:224px;overflow:hidden;border:1px solid var(--line);border-radius:4px}.shot img{display:block;width:auto;max-width:none}
.others{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px;display:grid;gap:10px}
.test-head .when{margin-left:auto}.tid{font-size:11px;font-weight:600;color:var(--accent-ink);background:var(--accent-bg);border-radius:4px;padding:1px 5px;flex:none}
@media (max-width:640px){summary{flex-wrap:wrap}.name{white-space:normal;flex-basis:calc(100% - 52px);display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3}.chips{flex-wrap:wrap;padding-left:46px}.when{margin-left:auto}.open{margin-left:0}}
</style></head><body><div class="wrap">
<h1>Traceability matrix: ${esc(spec.app)}</h1>
<p class="meta">${esc(scope)}Run against ${esc(baseUrl || 'APP_BASE_URL')}${revision ? `, revision ${esc(revision)}` : ''}. Requirements from ${esc(spec.source)}. Open a requirement to see its tests; click a test for its trace and screenshots.</p>
<div class="top">
<span class="pct" id="pct">${Math.round(pct(summary.pass))}%</span>
<div class="of"><b>passed</b><span id="of">${summary.pass} of ${summary.total} requirements</span></div>
<button type="button" class="open ghost" id="rerun" hidden>Rerun tests</button><a class="open" href="html-report/index.html">Open the full report</a>
</div>
<div class="bar" aria-hidden="true"><i class="pass" id="bar-pass" style="width:${pct(summary.pass)}%"></i><i class="fail" id="bar-fail" style="width:${pct(summary.fail)}%"></i><i class="warn" id="bar-warn" style="width:${pct(summary.flaky + summary.blocked)}%"></i></div>
<div class="counts" id="counts">
<button type="button" class="filter" id="filter" title="Show every requirement"></button>
<button type="button" class="count pass" data-count="pass" title="Show only these">${summary.pass} passed</button><button type="button" class="count fail" data-count="fail" title="Show only these">${summary.fail} failed</button>
<button type="button" class="count warn" data-count="flaky" title="Show only these">${summary.flaky} flaky</button><button type="button" class="count warn" data-count="blocked" title="Show only these">${summary.blocked} blocked</button>
<button type="button" class="count none" data-count="none" title="Show only these">${summary.notCovered} not covered</button>
<span class="last">Tests: ${testCount('passed')} of ${tests.length} passed · Last run ${shownTime(runAt.toISOString())}</span>
</div>
${summaryTable}
<p class="rerun" id="rerun-hint">Changed the app? To rerun the tests from this page, open a terminal in this pack's folder and run <code>npm start</code>. Or run <code>npm test</code> there, or ask Claude to rerun the tests, then reload this page.</p>
<div class="progress" id="progress" hidden><div class="progress-head"><b id="progress-title">Running the tests…</b><span id="progress-count"></span></div><div class="bar"><i class="pass" id="progress-bar" style="width:0"></i></div><pre id="progress-log"></pre></div>
${sections.join('\n')}
${strayTags.length ? `<p class="meta">Tagged with ids requirements.json doesn't have: ${esc(strayTags.join(', '))}</p>` : ''}
</div>
<script>
(() => {
  // Local times in place of UTC.
  for (const t of document.querySelectorAll('time[datetime]'))
    t.textContent = new Date(t.dateTime).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  // A chip shows only the requirements it names, and the numbers follow what is shown.
  // A count (passed, failed...) then narrows the list to that result.
  const rows = [...document.querySelectorAll('.row')];
  const filter = document.getElementById('filter');
  const words = { pass: 'passed', fail: 'failed', flaky: 'flaky', blocked: 'blocked', none: 'not covered' };
  let tag = '', kind = '';
  const show = () => {
    const lower = tag.toLowerCase();
    let n = { pass: 0, fail: 0, flaky: 0, blocked: 0, none: 0 }, total = 0;
    for (const r of rows) {
      const tagged = !tag || JSON.parse(r.dataset.chips).some((c) => c.toLowerCase() === lower);
      if (tagged) { n[r.dataset.kind]++; total++; }
      r.classList.toggle('hidden', !tagged || (kind && r.dataset.kind !== kind));
    }
    for (const s of document.querySelectorAll('section')) s.hidden = Boolean(tag || kind) && !s.querySelector('.row:not(.hidden)');
    const p = (k) => (total ? (100 * n[k]) / total : 0);
    document.getElementById('pct').textContent = Math.round(p('pass')) + '%';
    document.getElementById('of').textContent = n.pass + ' of ' + total + ' requirements' + (tag ? ' tagged ' + tag : '');
    document.getElementById('bar-pass').style.width = p('pass') + '%';
    document.getElementById('bar-fail').style.width = p('fail') + '%';
    document.getElementById('bar-warn').style.width = p('flaky') + p('blocked') + '%';
    for (const c of document.querySelectorAll('[data-count]')) {
      c.textContent = n[c.dataset.count] + ' ' + words[c.dataset.count];
      c.hidden = n[c.dataset.count] === 0;
      c.setAttribute('aria-pressed', String(c.dataset.count === kind));
    }
    const label = [tag && 'tagged ' + tag, kind && words[kind] + ' only'].filter(Boolean).join(', ');
    filter.textContent = label ? label + ' ×' : '';
    filter.classList.toggle('on', Boolean(label));
  };
  document.addEventListener('click', (e) => {
    const c = e.target.closest('[data-chip]');
    const k = e.target.closest('[data-count]');
    if (c) { e.preventDefault(); tag = c.dataset.chip; show(); }
    else if (k) { kind = kind === k.dataset.count ? '' : k.dataset.count; show(); }
  });
  filter.addEventListener('click', () => { tag = ''; kind = ''; show(); });
  show();

  // Served by npm start: Rerun tests runs the whole suite on this machine and reloads the
  // page with the new results; Rerun on a requirement runs only its tests, into
  // evidence/subset, and shows its new result on the row, beside the full run's. Opened as a
  // file, the page says how to get there.
  const button = document.getElementById('rerun');
  if (!location.protocol.startsWith('http')) return;
  const isFull = ${!subset.length};
  const fullRunAt = '${runAt.toISOString()}';
  const KIND = { 'Pass': 'pass', 'Pass (partial)': 'pass', 'Fail': 'fail', 'Flaky': 'warn', 'Blocked': 'warn', 'Not covered': 'none' };
  fetch('/api/status', { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)).then(async (status) => {
    if (!status?.token) return;
    const total = ${tests.length};
    document.getElementById('rerun-hint').hidden = true;
    button.hidden = false;
    if (!status.setUp) button.title = 'The first run installs the pack and its browser, which takes a few minutes.';
    for (const a of document.querySelectorAll('.row-actions')) a.hidden = false;
    const progress = document.getElementById('progress');
    const log = document.getElementById('progress-log');
    const busy = (label) => {
      button.disabled = true;
      for (const b of document.querySelectorAll('.rerun-one')) b.disabled = true;
      if (label) label.textContent = 'Running…';
    };

    // The last single-requirement rerun, if it is newer than the full run.
    if (isFull) {
      const sub = await fetch('subset/summary.json', { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
      if (sub && sub.runAt > fullRunAt) {
        const when = new Date(sub.runAt).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        for (const q of sub.requirements ?? []) {
          const row = document.querySelector('.row[data-id="' + CSS.escape(q.id) + '"]');
          if (!row) continue;
          const again = row.querySelector('.again');
          again.hidden = false;
          again.className = 'again ' + (KIND[q.verdict] ?? 'none');
          again.textContent = 'RERUN: ' + q.verdict.toUpperCase();
          again.title = 'Rerun on its own at ' + when + '. The full run said ' + row.querySelector('.when').textContent.split(' · ')[0] + '.';
          const result = row.querySelector('.rerun-result');
          if (result) result.innerHTML = 'Rerun on its own at ' + when + ': <b>' + q.verdict + '</b> · <a href="subset/html-report/index.html">its report</a> · <a href="subset/traceability-matrix.html">its matrix</a>';
        }
      }
    }
    // Back on the requirement that was just rerun.
    const back = location.hash && document.getElementById(location.hash.slice(1));
    if (back) { back.querySelector('details').open = true; back.scrollIntoView({ block: 'center' }); }

    const watch = (ids, label) => {
      busy(label);
      if (ids.length) {
        const row = document.querySelector('.row[data-id="' + CSS.escape(ids[0]) + '"]');
        row?.querySelector('.row-actions')?.after(progress);
        document.getElementById('progress-title').textContent = 'Rerunning ' + ids.join(', ') + '…';
      } else button.textContent = 'Running…';
      progress.hidden = false;
      const events = new EventSource('/api/events?token=' + status.token);
      events.onmessage = (e) => {
        const m = JSON.parse(e.data);
        if (m.finished) {
          events.close();
          document.getElementById('progress-title').textContent = m.code === 0 ? 'Every test passed. Loading the new results…' : 'Run finished. Loading the new results…';
          setTimeout(() => {
            // Back on the requirement after a single rerun; at the top after a full one.
            history.replaceState(null, '', location.pathname + (m.ids?.length ? '#req-' + m.ids[0] : ''));
            location.reload();
          }, 1200);
          return;
        }
        log.textContent += m.line + '\\n';
        log.scrollTop = log.scrollHeight;
        const done = Math.min(m.done, m.total || total);
        document.getElementById('progress-count').textContent = done + ' of ' + (m.total || total) + ' tests';
        document.getElementById('progress-bar').style.width = (100 * done) / (m.total || total || 1) + '%';
      };
    };
    if (status.running) watch(status.ids ?? []);
    const start = async (ids, n, label) => {
      const q = ids.map((id) => '&id=' + encodeURIComponent(id)).join('');
      const r = await fetch('/api/run?total=' + n + q, { method: 'POST', headers: { 'x-pack-token': status.token } });
      if (r.ok) watch(ids, label);
      // A run is already going, maybe from another tab: show that run, full or single.
      else if (r.status === 409) {
        const now = await fetch('/api/status', { cache: 'no-store' }).then((s) => s.json()).catch(() => null);
        if (now?.running) watch(now.ids ?? []);
      }
    };
    button.addEventListener('click', () => start([], total, null));
    document.addEventListener('click', (e) => {
      const b = e.target.closest('[data-rerun]');
      if (b) start([b.dataset.rerun], Number(b.dataset.total), b);
    });
  }).catch(() => {});
})();
</script>
</body></html>
`;
writeFileSync(path.join(out, 'traceability-matrix.html'), html);

// ---------- Playwright's report, in the same look ----------
// Copies report-theme.{css,js} beside the HTML report and links them, once, so "Open the
// full report" lands on a page that looks like this one. The report works without them.
const report = path.join(out, 'html-report', 'index.html');
if (existsSync(report)) {
  for (const f of ['report-theme.css', 'report-theme.js'])
    writeFileSync(path.join(out, 'html-report', f), readFileSync(path.join(root, 'scripts', f)));
  let page = readFileSync(report, 'utf8');
  if (!page.includes('report-theme.css')) {
    const project = results.config?.projects?.[0]?.name ?? 'chromium';
    // Plain index splices, no regex: the report is one large file.
    const head = page.indexOf('</head>');
    const body = page.lastIndexOf('</body>');
    if (head >= 0 && body > head) {
      page =
        page.slice(0, head) +
        '<link rel="stylesheet" href="report-theme.css">' +
        page.slice(head, body) +
        `<script src="report-theme.js" data-app="${esc(spec.app)}" data-project="${esc(project)}"></script>` +
        page.slice(body);
      writeFileSync(report, page);
    }
  }
}

// ---------- JSON summary (read by the Implementation Report and the hosted dashboard) ----------
// Each requirement carries what the report's requirements list cites as evidence: its tests,
// their results, and links (relative to evidence/) to the matrix row, each test's report entry
// with its trace, and the failure screenshot.
writeFileSync(
  path.join(out, 'summary.json'),
  JSON.stringify(
    {
      app: spec.app,
      baseUrl,
      revision,
      runAt: runAt.toISOString(),
      os: process.env.RUNNER_OS ?? process.platform,
      subset,
      summary,
      byTier,
      tests: { total: tests.length, passed: testCount('passed'), failed: testCount('failed'), flaky: testCount('flaky'), skipped: testCount('skipped') },
      requirements: rows.map((r) => ({
        id: r.id,
        ...(r.merged?.length ? { merged: r.merged } : {}),
        verdict: r.verdict,
        why: r.why,
        source: r.cite,
        where: r.where.map((w) => (w.route ? `${w.name} (${route(w.route)})` : `${w.name} (not built)`)),
        matrix: `traceability-matrix.html#req-${r.id}`,
        tests: r.tests.map((t) => ({
          id: t.testId,
          title: t.title,
          file: t.file,
          status: t.status,
          ...(t.error || t.skipReason ? { reason: t.error || t.skipReason } : {}),
          steps: t.steps.map((st) => st.title),
          report: `html-report/index.html#?testId=${encodeURIComponent(t.id)}`,
          ...(t.screenshot ? { screenshot: rel(t.screenshot) } : {}),
        })),
      })),
      other: other.map((t) => ({ id: t.testId, title: t.title, status: t.status })),
    },
    null,
    2,
  ) + '\n',
);
function testCount(status) {
  return tests.filter((t) => t.status === status).length;
}

if (unnamed.length) console.warn(`Tests with no test id (testId('TEST-nnn')): ${unnamed.map((t) => t.title).join('; ')}`);
if (reused.length) console.warn(`Test ids on more than one test: ${reused.join(', ')}`);
if (strayTags.length) console.warn(`Tagged with ids requirements.json doesn't have: ${strayTags.join(', ')}`);
console.log(
  `${scope}Traceability matrix: ${summary.pass} pass, ${summary.fail} fail, ${summary.flaky} flaky, ${summary.blocked} blocked, ${summary.notCovered} not covered (of ${summary.total}).`,
);
for (const [t, s] of Object.entries(byTier)) console.log(`  ${tierLine(t, s)}`);
console.log(`  ${path.join(path.relative(root, out), 'traceability-matrix.html')}`);
