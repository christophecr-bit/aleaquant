import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
import {performance} from 'node:perf_hooks';
import worker from './worker.mjs';

const root = dirname(fileURLToPath(import.meta.url));
const assets = join(root, 'assets');
const manifest = JSON.parse(readFileSync(join(assets, 'index.json'), 'utf8'));
const months = readdirSync(assets).filter(f => /^keno-\d{4}-\d{2}\.json$/.test(f));
const sizes = months.map(name => ({name, bytes: readFileSync(join(assets, name)).length}));
const sorted = sizes.toSorted((a, b) => a.bytes - b.bytes);
const median = sorted[Math.floor(sorted.length / 2)];
const largest = sorted.at(-1);

let count = 0;
let duplicateDate = false;
const seen = new Set();
for (const name of months) {
  const month = name.slice(5, 12);
  const payload = JSON.parse(readFileSync(join(assets, name), 'utf8'));
  assert.equal(payload.month, month);
  assert.equal(payload.game_id, 'keno');
  const dates = new Set();
  for (const draw of payload.draws) {
    assert(!seen.has(draw.id), `duplicate ${draw.id}`);
    seen.add(draw.id);
    assert.equal(manifest.id_to_month[draw.id], month);
    assert(draw.date.startsWith(month));
    assert.equal(draw.main.length, draw.rule === 'keno-70-20-v1' ? 20 : 16);
    assert.equal(new Set(draw.main).size, draw.main.length);
    duplicateDate ||= dates.has(draw.date);
    dates.add(draw.date);
    count++;
  }
}
assert.equal(count, Object.keys(manifest.id_to_month).length);
assert.equal(count, 19452);
assert(duplicateDate, 'old Keno has two draws on the same date');

const mockedAssets = {fetch: async req => {
  const name = new URL(req.url).pathname.replace('/keno/', '');
  try { return new Response(readFileSync(join(assets, name)), {status: 200}); }
  catch { return new Response(null, {status: 404}); }
}};
const base = 'https://aleaquant.aleaquant.workers.dev';
for (const id of ['KE-1993001', 'KE-26350']) {
  const response = await worker.fetch(new Request(`${base}/tirages/keno/${id}/`), {ASSETS: mockedAssets});
  assert.equal(response.status, 200);
  const html = await response.text();
  assert(html.startsWith('<!doctype html>'));
  assert(html.includes(`<link rel="canonical" href="${base}/tirages/keno/${id}/">`));
  assert(html.includes('application/ld+json'));
  assert(html.includes(id));
}
const missing = await worker.fetch(new Request(`${base}/tirages/keno/KE-UNKNOWN/`), {ASSETS: mockedAssets});
assert.equal(missing.status, 404);
assert.equal(missing.headers.get('x-robots-tag'), 'noindex');
const absentShard = await worker.fetch(new Request(`${base}/tirages/keno/KE-26350/`), {
  ASSETS: {fetch: req => new URL(req.url).pathname.endsWith('index.json')
    ? mockedAssets.fetch(req) : Promise.resolve(new Response(null, {status: 404}))},
});
assert.equal(absentShard.status, 503);
assert.equal(absentShard.headers.get('cache-control'), 'no-store');
const head = await worker.fetch(new Request(`${base}/tirages/keno/KE-26350/`, {method: 'HEAD'}), {ASSETS: mockedAssets});
assert.equal(head.status, 200);
assert.equal(await head.text(), '');
const method = await worker.fetch(new Request(`${base}/tirages/keno/KE-26350/`, {method: 'POST'}), {ASSETS: mockedAssets});
assert.equal(method.status, 405);

function parseTime(name, repeats = 5000) {
  const raw = readFileSync(join(assets, name), 'utf8');
  for (let i = 0; i < 100; i++) JSON.parse(raw);
  const start = performance.now();
  for (let i = 0; i < repeats; i++) JSON.parse(raw);
  return (performance.now() - start) / repeats;
}
const result = {draws: count, months: months.length,
  median_shard: {...median, parse_ms: parseTime(median.name)},
  largest_shard: {...largest, parse_ms: parseTime(largest.name)},
  index_parse_ms: parseTime('index.json', 1000),
  checks: ['unique IDs', 'month mapping', 'draw sizes', 'old duplicate dates',
           'SSR canonical and JSON-LD', '404 noindex', '503 no-store', 'HEAD', '405']};
console.log(JSON.stringify(result, null, 2));
