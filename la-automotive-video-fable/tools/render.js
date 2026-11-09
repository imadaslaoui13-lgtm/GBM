// Renders index.html frame-exact via window.seek() to frames/%04d.png at 30 fps.
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const out = process.argv[2], FPS = 30, WORKERS = 4;
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const N = Math.round(25 * FPS);
  await Promise.all([...Array(WORKERS).keys()].map(async w => {
    const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
    await p.goto('file://' + path.resolve(__dirname, '../index.html') + '?render' + (process.env.NOTEXT ? '&notext' : ''));
    await p.waitForFunction(() => window.FONTS_READY);
    const c = p.locator('#c');
    for (let i = w; i < N; i += WORKERS) {
      await p.evaluate(t => window.seek(t), i / FPS);
      await c.screenshot({ path: `${out}/${String(i).padStart(4, '0')}.png` });
    }
  }));
  await b.close(); console.log('frames', N);
})();
