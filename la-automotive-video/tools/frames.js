// usage: node frames.js out_dir t1 t2 ...  -> PNG per time (1080x1920)
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [out, ...ts] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
  await p.goto('file://' + path.resolve(__dirname, '../index.html') + '?render');
  for (const t of ts) {
    await p.evaluate(t => window.seek(t), +t);
    await p.locator('#c').screenshot({ path: `${out}/f_${(+t).toFixed(2)}.png` });
  }
  if (errs.length) console.log('ERRORS', errs);
  await b.close();
})();
