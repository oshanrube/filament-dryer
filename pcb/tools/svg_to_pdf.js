// Export an SVG to a one-page PDF of the same size (needs Playwright).
// Run from the repo root:  node pcb/tools/svg_to_pdf.js pcb/schematic.svg pcb/schematic.pdf
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [,, file, out] = process.argv;
  const svg = fs.readFileSync(file, 'utf8');
  const m = svg.match(/viewBox="0 0 (\d+) (\d+)"/) || svg.match(/width="(\d+)" height="(\d+)"/);
  const [w, h] = [+m[1], +m[2]];
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setContent(`<html><head><style>@page{size:${w}px ${h}px;margin:0}body{margin:0}</style></head><body>${svg}</body></html>`);
  await p.pdf({ path: out, width: w + 'px', height: h + 'px', printBackground: true, pageRanges: '1' });
  await b.close();
})();
