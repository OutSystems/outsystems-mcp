// Goes with report-theme.css: adds the bar back to the traceability matrix, sorts the
// report's tags into requirement ids, the browser project and other tags, and colours the
// Given / When / Then keyword of each step. The report renders as it goes, so this re-runs
// on every change. Without it the report still works; it just keeps its own tag colours.
(() => {
  const me = document.currentScript;
  const bar = document.createElement('div');
  bar.className = 'pack-bar';
  const name = document.createElement('b');
  name.textContent = `Test report: ${me?.dataset.app ?? ''}`;
  const back = document.createElement('a');
  back.href = '../traceability-matrix.html';
  back.textContent = '← Traceability matrix';
  bar.append(name, back);
  document.body.prepend(bar);

  const ID = /^[A-Z][A-Z0-9]*-\d+[A-Z0-9-]*$/;
  const project = me?.dataset.project ?? 'chromium';
  const tidy = () => {
    for (const label of document.querySelectorAll('.label:not([data-pack])')) {
      const text = label.textContent.trim();
      label.dataset.pack = '1';
      label.classList.add(ID.test(text) ? 'pack-id' : text === project ? 'pack-project' : 'pack-tag');
    }
    for (const title of document.querySelectorAll('.tree-item-title:not([data-pack])')) {
      title.dataset.pack = '1';
      const walker = document.createTreeWalker(title, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        const m = node.nodeValue.match(/^(\s*)(Given|When|Then|And)(\s)/);
        if (!m) continue;
        const kw = document.createElement('span');
        kw.className = 'pack-kw';
        kw.textContent = m[2];
        node.nodeValue = node.nodeValue.slice(m[1].length + m[2].length);
        node.parentNode.insertBefore(kw, node);
        break;
      }
    }
  };
  new MutationObserver(tidy).observe(document.body, { childList: true, subtree: true });
  tidy();
})();
