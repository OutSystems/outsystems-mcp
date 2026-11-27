// The build loop's report (npm run screens): a verdict line first ("Screen tests: 3/4 PASS,
// 1 FAIL.", the line a BuildReport quotes, as in-app), then one line per spec that failed to
// load, one per failing test naming the step that failed, why and where its screenshot is,
// and one line with the passing tests (the first PASS_NAMES names, then "+K more"). A spec
// that fails to load counts as a FAIL in the verdict: its tests never ran, so the screen is
// not proven. Short however many tests pass, so reading it costs next to nothing, unlike a
// list reporter's per-test lines and full error frames.

import { relative } from 'node:path';

const ANSI = /\u001b\[[0-9;]*m/g;
// How many passing names the PASS line spells out; the rest are counted.
const PASS_NAMES = 20;

// The Given / When / Then step a failure happened in, as the test names it.
function failedStep(steps) {
  for (const step of steps) {
    if (step.error) return step.title;
  }
  return '';
}

// The error's first line, plus the locator and what was expected when Playwright names them.
function why(error) {
  const lines = String(error?.message ?? error?.value ?? 'failed').replace(ANSI, '').split('\n').map((l) => l.trim());
  const named = ['Locator:', 'Expected'].map((head) => lines.find((l) => l.startsWith(head)));
  return [lines.find(Boolean), ...named].filter(Boolean).join(' · ').slice(0, 300);
}

export default class CompactReporter {
  constructor() {
    this.results = new Map();
    this.errors = [];
  }

  // A spec that fails to compile or import never reaches onTestEnd: without this the run
  // would end in "No tests ran" or a PASS line with no word of what broke.
  onError(error) {
    const where = error?.location?.file ? `${relative(process.cwd(), error.location.file)}: ` : '';
    this.errors.push(`ERROR ${where}${why(error)}`);
  }

  printsToStdio() {
    return true;
  }

  onTestEnd(test, result) {
    // With retries a test ends more than once. Keep its last failing attempt: a flaky test's
    // last attempt passed, and has no error, step or screenshot to show.
    if (!this.results.has(test.id) || result.status !== 'passed') this.results.set(test.id, { test, result });
  }

  onEnd(run) {
    const passed = [];
    const skipped = [];
    const lines = [];
    let failed = 0;
    for (const { test, result } of this.results.values()) {
      const file = test.location.file.split(/[\\/]/).pop().replace(/\.spec\.ts$/, '');
      const name = `${file} › ${test.title}`;
      const outcome = test.outcome();
      // A test marked test.fail() whose body failed is 'expected' to Playwright and exits 0,
      // but the screen is broken: only a body that didn't fail is a PASS.
      const bodyFailed = ['failed', 'timedOut', 'interrupted'].includes(result.status);
      if (outcome === 'expected' && !bodyFailed) passed.push(name);
      else if (outcome === 'skipped') skipped.push(name);
      else {
        failed += 1;
        const step = failedStep(result.steps);
        const png = result.attachments.find((a) => a.contentType === 'image/png' && a.path);
        const shot = png ? relative(process.cwd(), png.path) : '';
        const label = outcome === 'flaky' ? 'FLAKY' : 'FAIL';
        const retry = outcome === 'flaky' ? ' (passed on retry)' : outcome === 'expected' ? ' (marked test.fail())' : '';
        lines.push(`${label} ${name}${retry}${step ? ` at "${step}"` : ''}: ${why(result.error)}${shot ? ` (screenshot: ${shot})` : ''}`);
      }
    }
    lines.unshift(...this.errors);
    // A spec that failed to load counts once in the total, so the pass fraction and the
    // failure count describe the same run.
    const ran = this.results.size;
    const total = ran + this.errors.length;
    const failing = failed + this.errors.length;
    const cutShort = ['interrupted', 'timedout'].includes(run.status)
      || (run.status === 'failed' && !failing);
    const verdict = [ran ? `Screen tests: ${passed.length}/${total} PASS` : `Screen tests: none ran (${run.status})`];
    if (failing) verdict.push(`${failing} FAIL`);
    if (ran && cutShort) verdict.push(`INCOMPLETE (${run.status})`);
    lines.unshift(`${verdict.join(', ')}.`);
    if (passed.length) {
      const more = passed.length > PASS_NAMES ? `; +${passed.length - PASS_NAMES} more` : '';
      lines.push(`PASS ${passed.length}/${total}: ${passed.slice(0, PASS_NAMES).join('; ')}${more}`);
    }
    if (skipped.length) lines.push(`SKIPPED ${skipped.length}: ${skipped.join('; ')}`);
    // A run cut short (a timeout, maxFailures, an interrupt), or one that failed with nothing
    // above to say why, must not read as green: the tests it never reached aren't listed.
    if (ran && cutShort) {
      lines.push(`INCOMPLETE (${run.status}): ${ran} test(s) reported; the run ended before the rest.`);
    }
    console.log(lines.join('\n'));
    // Exit as the verdict reads: a test.fail() test whose body failed is 'expected' to Playwright,
    // which would exit 0 although a screen is broken.
    return failing ? { status: 'failed' } : undefined;
  }
}
