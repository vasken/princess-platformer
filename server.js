// Minimal dev server: serves static files and exposes POST /api/save-levels
// so the editor can write levels.js directly to disk.
//
// Run:  node server.js   (or: npm start)
// Then: http://localhost:8080/         (game)
//       http://localhost:8080/editor    (level editor)
//
// For production: upload index.html, editor.html, levels.js to any static
// host. /api/save-levels will 404 and the editor falls back to a download.

'use strict';

const http = require('http');
const fs   = require('fs');
const path = require('path');

const PORT = Number(process.env.PORT) || 8080;
const ROOT = __dirname;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'text/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
};

// Only top-level app files and project assets may be served. Anything else → 404.
const ALLOWED = new Set(['index.html', 'editor.html', 'levels.js', 'assets/princess-main.png']);

function send(res, status, body, headers = {}) {
  res.writeHead(status, { 'Cache-Control': 'no-store', ...headers });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    const pathname = url.pathname;

    // --- API: save levels.js ---
    if (req.method === 'POST' && pathname === '/api/save-levels') {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const body = Buffer.concat(chunks).toString('utf8');
      if (!body.includes('window.LEVELS')) {
        return send(res, 400, '{"ok":false,"error":"payload missing window.LEVELS"}',
          { 'Content-Type': 'application/json' });
      }
      fs.writeFileSync(path.join(ROOT, 'levels.js'), body);
      console.log(`[save] wrote levels.js (${body.length} bytes)`);
      return send(res, 200, '{"ok":true}', { 'Content-Type': 'application/json' });
    }

    // --- Static files ---
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      return send(res, 405, 'Method not allowed');
    }

    let file;
    if (pathname === '/' || pathname === '/index.html') file = 'index.html';
    else if (pathname === '/editor' || pathname === '/editor.html') file = 'editor.html';
    else file = pathname.replace(/^\/+/, '');

    if (!ALLOWED.has(file)) return send(res, 404, 'Not found');

    const filePath = path.join(ROOT, file);
    if (!fs.existsSync(filePath)) return send(res, 404, 'Not found');

    const mime = MIME[path.extname(file).toLowerCase()] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'no-store' });
    if (req.method === 'HEAD') return res.end();
    fs.createReadStream(filePath).pipe(res);
  } catch (err) {
    console.error(err);
    send(res, 500, 'Internal error');
  }
});

server.listen(PORT, () => {
  console.log(`\n  🎮  Game    http://localhost:${PORT}/`);
  console.log(`  ✏️   Editor  http://localhost:${PORT}/editor\n`);
});
