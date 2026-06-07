import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const files = [
  path.join(__dirname, 'package.json'),
  path.join(__dirname, 'main.js'),
  path.join(__dirname, 'preload.js'),
  path.join(root, 'ui', 'index.html'),
  path.join(root, 'bin', 'hapa-graphify-desktop.sh')
];

const missing = files.filter((file) => !existsSync(file));
const main = readFileSync(path.join(__dirname, 'main.js'), 'utf8');
const checks = {
  filesExist: missing.length === 0,
  startsService: main.includes('hapa_graphify') && main.includes('serve'),
  opensUi: main.includes('/ui'),
  dataOutsideBundle: main.includes('cwd: ROOT')
};

if (missing.length) checks.missing = missing;
const ok = Object.values(checks).every((value) => value === true || Array.isArray(value));
console.log(JSON.stringify({ ok, checks }, null, 2));
process.exit(ok ? 0 : 1);
