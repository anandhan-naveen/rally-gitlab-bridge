import express from 'express';
import multer from 'multer';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { config } from './config.js';
import { saveSnapshot, summary } from './snapshot.js';
import { preview, importScope, syncScope, status } from './service.js';

const app = express();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } });
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const helperPath = path.resolve(__dirname, '../public/rally-browser-helper.js');

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

function page(message = '') {
  const s = summary();
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rally ↔ GitLab Bridge</title><style>
  body{font-family:system-ui,-apple-system,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;color:#1f2937;background:#f8fafc}h1{margin-bottom:4px}.card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:20px;margin:18px 0;box-shadow:0 4px 18px rgba(0,0,0,.04)}code,pre{background:#f1f5f9;padding:3px 6px;border-radius:6px}button,.btn{display:inline-block;background:#111827;color:#fff;padding:10px 14px;border:0;border-radius:9px;text-decoration:none;cursor:pointer}input,select{padding:9px;border:1px solid #cbd5e1;border-radius:8px;margin:4px}.ok{color:#047857}.muted{color:#64748b}</style></head><body>
  <h1>Rally ↔ GitLab Bridge</h1><div class="muted">Node.js v0.3.0 · Browser SSO snapshot mode</div>
  ${message ? `<div class="card ok">${message}</div>` : ''}
  <div class="card"><h2>Rally snapshot</h2><p>${s.available ? `Loaded: <b>${s.stories}</b> stories, <b>${s.tasks}</b> tasks` : 'No snapshot loaded yet.'}</p><p><a class="btn" href="/rally/browser-helper">Create snapshot from logged-in Rally</a></p><form method="post" action="/rally/snapshot" enctype="multipart/form-data"><input type="file" name="snapshot" accept="application/json" required><button>Upload snapshot</button></form></div>
  <div class="card"><h2>Preview</h2><form method="get" action="/preview"><select name="type"><option>story</option><option>feature</option><option>quarter</option><option>all</option></select><input name="value" placeholder="US1234 / F1234 / Q4-2026"><button>Preview</button></form></div>
  <div class="card"><h2>CLI</h2><pre>npm run bridge -- preview story US1234
npm run bridge -- import feature F1234 --dry-run
npm run bridge -- sync feature F1234 --dry-run</pre></div>
  <div class="card"><h2>Safety model</h2><p>Rally browser credentials never enter this app. GitLab → Rally writes remain disabled in browser-snapshot mode; the bridge reports proposed Rally updates instead.</p></div>
  </body></html>`;
}

app.get('/', (_req, res) => res.type('html').send(page()));
app.get('/health', (_req, res) => res.json({ status: 'ok', version: '0.3.0', runtime: 'node' }));
app.get('/status', (_req, res) => res.json(status()));
app.get('/preview', (req, res) => {
  try { res.json(preview(String(req.query.type || 'all'), String(req.query.value || ''))); }
  catch (e) { res.status(400).json({ error: e.message }); }
});
app.post('/import', async (req, res) => {
  try { res.json(await importScope(req.body.type || 'all', req.body.value || '', { dryRun: Boolean(req.body.dryRun) })); }
  catch (e) { res.status(400).json({ error: e.message }); }
});
app.post('/sync', async (req, res) => {
  try { res.json(await syncScope(req.body.type || 'all', req.body.value || '', { dryRun: Boolean(req.body.dryRun) })); }
  catch (e) { res.status(400).json({ error: e.message }); }
});
app.post('/rally/snapshot', upload.single('snapshot'), (req, res) => {
  try {
    if (!req.file) throw new Error('Choose a snapshot JSON file.');
    const result = saveSnapshot(JSON.parse(req.file.buffer.toString('utf8')));
    res.type('html').send(page(`Snapshot loaded: ${result.stories} stories and ${result.tasks} tasks.`));
  } catch (e) { res.status(400).type('html').send(page(`Snapshot error: ${e.message}`)); }
});
app.get('/rally/browser-helper.js', (_req, res) => res.download(helperPath, 'rally-browser-helper.js'));
app.get('/rally/browser-helper', (_req, res) => res.type('html').send(`<!doctype html><html><body style="font-family:system-ui;max-width:780px;margin:40px auto"><h1>Rally browser helper</h1><p>This helper does not read localStorage, sessionStorage, cookies, or SSO tokens.</p><ol><li><a href="/rally/browser-helper.js">Download the helper</a>.</li><li>Sign in to Rally normally with company SSO.</li><li>Open Developer Tools → Console on the Rally page.</li><li>Open the downloaded JS file, copy its contents, paste them in the Rally console and run it.</li><li>Choose story, feature or quarter. The browser downloads a JSON snapshot.</li><li>Upload that JSON on the local bridge dashboard.</li></ol><p><a href="/">← Back</a></p></body></html>`));

app.listen(config.port, () => console.log(`Rally ↔ GitLab Bridge: http://127.0.0.1:${config.port}`));
