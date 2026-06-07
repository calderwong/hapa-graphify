const { app, BrowserWindow, shell } = require('electron');
const { spawn } = require('node:child_process');
const path = require('node:path');
const http = require('node:http');

const ROOT = path.resolve(__dirname, '..');
const HOST = process.env.HAPA_GRAPHIFY_HOST || '127.0.0.1';
const PORT = Number(process.env.HAPA_GRAPHIFY_PORT || 8796);
const URL = `http://${HOST}:${PORT}/ui`;

let service = null;
let win = null;

function startService() {
  if (service) return service;
  service = spawn(process.env.PYTHON || 'python3', ['-m', 'hapa_graphify', 'serve', '--host', HOST, '--port', String(PORT)], {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONPATH: ROOT }
  });
  service.stdout.on('data', (chunk) => console.log(`[hapa-graphify] ${chunk.toString().trim()}`));
  service.stderr.on('data', (chunk) => console.error(`[hapa-graphify] ${chunk.toString().trim()}`));
  service.on('exit', (code) => {
    console.log(`[hapa-graphify] service exited ${code}`);
    service = null;
  });
  return service;
}

function waitForHealth(attempts = 60) {
  return new Promise((resolve, reject) => {
    const tick = (remaining) => {
      const req = http.get(`http://${HOST}:${PORT}/health`, (res) => {
        res.resume();
        if (res.statusCode === 200) resolve(true);
        else if (remaining <= 0) reject(new Error(`health status ${res.statusCode}`));
        else setTimeout(() => tick(remaining - 1), 250);
      });
      req.on('error', () => {
        if (remaining <= 0) reject(new Error('service health timeout'));
        else setTimeout(() => tick(remaining - 1), 250);
      });
      req.setTimeout(500, () => req.destroy());
    };
    tick(attempts);
  });
}

async function createWindow() {
  startService();
  await waitForHealth();
  win = new BrowserWindow({
    width: 1320,
    height: 880,
    minWidth: 980,
    minHeight: 680,
    title: 'Hapa Graphify',
    backgroundColor: '#020617',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
  await win.loadURL(URL);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('before-quit', () => {
  if (service) service.kill();
});
