// AleaQuant V0 — Tirages, Atlas, Géométries, Lab. Données : data/*.json produites par engine/.
// Aucune prédiction : tout est loi exacte, historique daté ou géométrie descriptive.
const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, ...kids) => { const e = document.createElement(tag); for (const [k, v] of Object.entries(attrs)) { if (k === 'class') e.className = v; else if (k === 'text') e.textContent = v; else e.setAttribute(k, v); } e.append(...kids); return e; };
const svgEl = (tag, attrs = {}) => { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); return e; };
const put = (parent, node) => (parent.append(node), node);
const nb = (n) => Number(n).toLocaleString('fr-FR');
const pct = (p, d) => (100 * p).toLocaleString('fr-FR', { maximumFractionDigits: d ?? (p < 0.01 ? 2 : 1), minimumFractionDigits: d ?? (p < 0.01 ? 2 : 1) }) + ' %';
const fmtP = (p) => p < 0.001 ? '< 0,001' : p.toLocaleString('fr-FR', { maximumFractionDigits: 3 });
const dateFr = (iso) => new Date(iso + 'T12:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
const RARITY = { COMMON: 'courante', UNCOMMON: 'peu courante', RARE: 'rare', VERY_RARE: 'très rare' };
const rarity = (p) => p >= 0.1 ? 'COMMON' : p >= 0.01 ? 'UNCOMMON' : p >= 0.001 ? 'RARE' : 'VERY_RARE';
const C = { th: '#2a78d6', obs: '#eb6834', ink: '#123633', muted: '#526962', grid: '#dfe5dc' };

async function load(name) { const r = await fetch('data/' + name); if (!r.ok) throw new Error(name); return r.json(); }

// ------------------------------------------------------------ petite loi (sparkline)
function spark(svg, law, key) {
  const vals = law.values, p = law.p, n = vals.length, W = 300, H = 46;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.replaceChildren();
  const max = Math.max(...p), bw = W / n;
  vals.forEach((v, i) => {
    const h = Math.max(1, (p[i] / max) * (H - 4)), on = v === key;
    put(svg, svgEl('rect', { x: i * bw + (bw > 3 ? 0.5 : 0), y: H - h, width: Math.max(bw - (bw > 3 ? 1 : 0), 0.8), height: h, rx: bw > 6 ? 1.5 : 0, fill: on ? C.obs : '#b7d3f6' }));
  });
  if (!vals.includes(key)) put(svg, svgEl('text', { x: W, y: 12, 'text-anchor': 'end', fill: C.muted, 'font-size': 11 })).textContent = 'hors des 20 classes les plus peuplées';
}

// ------------------------------------------------------------ Tirages
function lawIndex(law) {
  const idx = new Map(law.values.map((v, i) => [v, i]));
  let acc = 0; const le = law.p.map((q) => (acc += q));
  return { idx, le };
}
function renderDraw(row, ctx) {
  const [id, date, rule, main, stars, mvals, svals] = row;
  $('#draw-balls').replaceChildren(...main.map((n) => el('span', { class: 'ball', text: String(n).padStart(2, '0') })), el('span', { class: 'sep' }), ...stars.map((n) => el('span', { class: 'ball star', text: String(n).padStart(2, '0') })));
  const pos = ctx.rows.indexOf(row);
  $('#draw-meta').textContent = `${dateFr(date)} · tirage ${id} · ${pos} tirages antérieurs dans l’historique · règle ${rule}`;
  // Pascal
  const prior = ctx.rows.slice(0, pos);
  const seen = (t) => { const s = new Set(); prior.forEach((r) => comb(r[3], t).forEach((c) => s.add(c.join('-')))); return comb(main, t).filter((c) => s.has(c.join('-'))).length; };
  $('#pascal-callout').replaceChildren(el('span', { class: 'big', text: '10 = 10' }), el('div', {}, el('strong', { text: 'Autant de paires que de triplets : C(5,2) = C(5,3).' }), el('p', { text: `Choisir un triplet parmi 5 numéros revient à choisir la paire laissée de côté : symétrie du triangle de Pascal. Mais le domaine compte 1 225 paires contre 19 600 triplets. Avant ce tirage, ${seen(2)} de ses 10 paires et ${seen(3)} de ses 10 triplets étaient déjà sortis ensemble ; ${seen(4)} de ses 5 quadruplets.` })));
  const cards = [];
  const add = (mid, value, law, label) => {
    const { idx, le } = lawIndex(law); const i = idx.get(value); const pc = i === undefined ? null : law.p[i];
    const numeric = !Number.isNaN(Number(value)) && !String(value).includes('-');
    const card = el('div', { class: 'mcard' });
    const h = el('h4', { text: label });
    const shown = String(value).replaceAll('-', '·').replace(/\.0$/, '').replace('.', ',');
    card.append(h, el('div', { class: 'val', text: shown }));
    if (pc !== null) {
      const r = rarity(pc); const chip = el('span', { class: 'chip ' + r, text: RARITY[r] });
      let sub = `classe : ${pct(pc)} des combinaisons`;
      if (numeric) { const lo = le[i], hi = 1 - le[i] + pc, tail = Math.min(lo, hi); if (tail < 0.05) card.querySelector('.val').append(el('span', { class: 'chip tail', text: 'queue ' + pct(tail) })); sub += ` · ${pct(lo)} ≤ ce niveau`; }
      h.append(chip); card.append(el('div', { class: 'sub', text: sub }));
    } else card.append(el('div', { class: 'sub', text: 'classe fine (hors des 20 plus peuplées)' }));
    if (pc !== null) { const s = svgEl('svg', { role: 'img', 'aria-label': `Loi exacte de ${label}, valeur du tirage en orange` }); spark(s, law, value); card.append(s); }
    cards.push(card);
  };
  ctx.draws.main_fields.forEach((f, i) => add('main.' + f, mvals[i], ctx.laws.metrics['main.' + f], ctx.laws.metrics['main.' + f].label));
  if (svals) ctx.draws.star_fields.forEach((f, i) => add('stars.' + f, svals[i], ctx.laws.metrics['stars.' + f], ctx.laws.metrics['stars.' + f].label));
  $('#draw-metrics').replaceChildren(...cards);
}
function comb(arr, k) { const out = []; const rec = (s, acc) => { if (acc.length === k) { out.push(acc.slice()); return; } for (let i = s; i < arr.length; i++) { acc.push(arr[i]); rec(i + 1, acc); acc.pop(); } }; rec(0, []); return out; }

// ------------------------------------------------------------ Atlas : cooccurrences
function diverging(z) { // bleu ← gris → rouge, saturé à |z| = 3.5
  const t = Math.max(-1, Math.min(1, z / 3.5)); const mid = [240, 239, 236];
  const end = t < 0 ? [42, 120, 214] : [227, 73, 72]; const a = Math.abs(t);
  return `rgb(${mid.map((m, i) => Math.round(m + (end[i] - m) * a)).join(',')})`;
}
function renderCooc(atlas) {
  const co = atlas.cooccurrence, cv = $('#cooc'), g = cv.getContext('2d'), N = 50, S = cv.width / N;
  const z = Array.from({ length: N }, () => new Array(N).fill(0)), cnt = Array.from({ length: N }, () => new Array(N).fill(0));
  let best = { z: 0 };
  co.pairs.forEach(([a, b, c]) => { const v = (c - co.expected) / co.sd; z[a - 1][b - 1] = z[b - 1][a - 1] = v; cnt[a - 1][b - 1] = cnt[b - 1][a - 1] = c; if (Math.abs(v) > Math.abs(best.z)) best = { a, b, c, z: v }; });
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) { g.fillStyle = i === j ? '#ffffff' : diverging(z[i][j]); g.fillRect(j * S, i * S, S, S); }
  g.strokeStyle = 'rgba(18,54,51,.18)'; g.lineWidth = 1;
  for (let k = 10; k < N; k += 10) { g.beginPath(); g.moveTo(k * S, 0); g.lineTo(k * S, cv.height); g.moveTo(0, k * S); g.lineTo(cv.width, k * S); g.stroke(); }
  $('#cooc-ramp').style.background = `linear-gradient(90deg, ${diverging(-3.5)}, ${diverging(0)}, ${diverging(3.5)})`;
  const tip = $('#cooc-tip');
  cv.addEventListener('mousemove', (e) => { const r = cv.getBoundingClientRect(); const j = Math.floor((e.clientX - r.left) / r.width * N), i = Math.floor((e.clientY - r.top) / r.height * N); if (i < 0 || j < 0 || i >= N || j >= N || i === j) { tip.hidden = true; return; } tip.hidden = false; tip.style.left = (e.clientX - r.left) + 'px'; tip.style.top = (e.clientY - r.top) + 'px'; tip.textContent = `Paire ${i + 1}–${j + 1} : ${cnt[i][j]} fois (attendu ${co.expected.toFixed(1).replace('.', ',')}) · z = ${z[i][j].toFixed(2).replace('.', ',')}`; });
  cv.addEventListener('mouseleave', () => (tip.hidden = true));
  const kv = [['Tirages', nb(co.n)], ['Attendu par paire', co.expected.toFixed(2).replace('.', ',') + ' fois'], ['Écart-type attendu', co.sd.toFixed(2).replace('.', ',')], ['Paire la plus éloignée', `${best.a}–${best.b} : ${best.c} fois, z = ${best.z.toFixed(2).replace('.', ',')}`], ['Max |z| sous hasard pur', `médiane ${co.null_max_abs_z.median.toFixed(2).replace('.', ',')}, 95 % sous ${co.null_max_abs_z.p95.toFixed(2).replace('.', ',')}`]];
  $('#cooc-stats').replaceChildren(...kv.flatMap(([k, v]) => [el('dt', { text: k }), el('dd', { text: v })]));
  // fréquences des numéros
  const svg = $('#freq-chart'); svg.replaceChildren(); const W = 420, H = 190, L = 34, B = 22, T = 22;
  const f = co.freq, lo = Math.min(...f, co.freq_expected) * 0.9, hi = Math.max(...f) * 1.03, y = (v) => T + (H - T - B) * (1 - (v - lo) / (hi - lo)), bw = (W - L) / 50;
  put(svg, svgEl('text', { x: 0, y: 12, class: 'title' })).textContent = 'Sorties de chaque numéro (attendu en trait)';
  [lo, co.freq_expected, hi].forEach((v) => { put(svg, svgEl('text', { x: L - 4, y: y(v) + 4, 'text-anchor': 'end' })).textContent = Math.round(v); });
  f.forEach((v, i) => { const r = svgEl('rect', { x: L + i * bw + 1, y: y(v), width: bw - 2, height: y(lo) - y(v), rx: 1.5, fill: '#86b6ef' }); r.append(svgEl('title')); r.firstChild.textContent = `Numéro ${i + 1} : ${v} sorties`; svg.append(r); });
  put(svg, svgEl('line', { x1: L, x2: W, y1: y(co.freq_expected), y2: y(co.freq_expected), stroke: C.ink, 'stroke-width': 1.5, 'stroke-dasharray': '4 3' }));
  [1, 10, 20, 30, 40, 50].forEach((k) => { put(svg, svgEl('text', { x: L + (k - 0.5) * bw, y: H - 6, 'text-anchor': 'middle' })).textContent = k; });
}

// ------------------------------------------------------------ Géométries
function seqBlue(t) { const a = [236, 240, 230], b = [16, 66, 129]; return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * t)).join(',')})`; }
function jaccard(grids) { const sets = grids.map((g) => new Set(g[0])); return sets.map((a) => sets.map((b) => { let i = 0; a.forEach((x) => b.has(x) && i++); return i / (a.size + b.size - i); })); }
function renderGeo(ctx) {
  const gen = ctx.gen, item = gen.items.find((x) => x.id === $('#geo-select').value) || gen.items[0];
  const J = jaccard(item.grids), N = J.length, cv = $('#jaccard'), g = cv.getContext('2d'); const S = Math.floor(300 / N); cv.width = cv.height = S * N;
  let jmax = 0; for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) if (i !== j) jmax = Math.max(jmax, J[i][j]);
  const scale = Math.max(jmax, 0.25);
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) { g.fillStyle = i === j ? '#123633' : seqBlue(J[i][j] / scale); g.fillRect(j * S, i * S, S - (S > 6 ? 1 : 0), S - (S > 6 ? 1 : 0)); }
  $('#jac-ramp').style.background = `linear-gradient(90deg, ${seqBlue(0)}, ${seqBlue(1)})`; $('#jac-max').textContent = scale.toFixed(2).replace('.', ',');
  const tip = $('#jac-tip');
  cv.onmousemove = (e) => { const r = cv.getBoundingClientRect(); const j = Math.floor((e.clientX - r.left) / r.width * N), i = Math.floor((e.clientY - r.top) / r.height * N); if (i < 0 || j < 0 || i >= N || j >= N) { tip.hidden = true; return; } tip.hidden = false; tip.style.left = (e.clientX - r.left) + 'px'; tip.style.top = (e.clientY - r.top) + 'px'; const a = item.grids[i][0], b = item.grids[j][0]; tip.textContent = i === j ? `Grille ${i + 1} : ${a.join(' ')}` : `Grilles ${i + 1} et ${j + 1} : ${a.filter((x) => b.includes(x)).length} numéros communs · Jaccard ${J[i][j].toFixed(2).replace('.', ',')}`; };
  cv.onmouseleave = () => (tip.hidden = true);
  const geo = item.geometry;
  const kv = [['Famille', item.family + (item.roles && item.roles.length ? ' · ' + item.roles.join(', ') : '')], ...(item.aliases && item.aliases.length ? [['Alias', item.aliases.join(', ')]] : []), ...(item.objective ? [['Objectif', item.objective]] : []), ['Grilles', geo.grids], ['Union des numéros', `${geo.union} sur ${gen.domain}`],
    ...(geo.second ? [[`Union ${gen.second_label}`, `${geo.second.union} sur ${gen.second_domain} · overlap max ${geo.second.overlap_max}`]] : []), ['Overlap moyen / max', `${geo.overlap_mean.toFixed(2).replace('.', ',')} / ${geo.overlap_max}`], ['Paires couvertes', `${nb(geo.coverage['2'].covered)} sur ${nb(geo.coverage['2'].possible)} · ${nb(geo.coverage['2'].collisions)} collisions`], ['Triplets couverts', `${nb(geo.coverage['3'].covered)} sur ${nb(geo.coverage['3'].possible)}`], ['Dispersion des occurrences', geo.occurrence_sd.toFixed(2).replace('.', ',')], ['SHA-256', item.sha256.slice(0, 16) + '…']];
  $('#geo-stats').replaceChildren(...kv.flatMap(([k, v]) => [el('dt', { text: k }), el('dd', { text: String(v) })]));
  // histogramme des overlaps
  const svg = $('#overlap-chart'); svg.replaceChildren(); const hist = geo.overlap_hist, W = 420, H = 180, L = 30, B = 24, T = 44, n = hist.length, bw = (W - L) / n, max = Math.max(...hist);
  put(svg, svgEl('text', { x: 0, y: 12, class: 'title' })).textContent = `Numéros communs entre deux grilles (${nb(hist.reduce((a, b) => a + b, 0))} paires de grilles)`;
  hist.forEach((v, i) => { const h = (H - T - B) * v / max; const r = svgEl('rect', { x: L + i * bw + 3, y: H - B - h, width: bw - 6, height: Math.max(h, v ? 1 : 0), rx: 3, fill: C.th }); r.append(svgEl('title')); r.firstChild.textContent = `${i} en commun : ${v} paires`; svg.append(r); put(svg, svgEl('text', { x: L + (i + 0.5) * bw, y: H - 8, 'text-anchor': 'middle' })).textContent = i; if (v) put(svg, svgEl('text', { x: L + (i + 0.5) * bw, y: H - B - h - 4, 'text-anchor': 'middle' })).textContent = v; });
  // EuroMillions : loi exacte des gagnantes
  const em = $('#em-exact'); em.hidden = gen.game !== 'euromillions';
  if (gen.game === 'euromillions') renderWin(gen, item);
  document.querySelectorAll('#em-table tbody tr').forEach((tr) => tr.classList.toggle('sel', tr.dataset.id === item.id));
}
function renderWin(gen, item) {
  const ref = gen.items.find((x) => x.id === 'RANDOM_001');
  const svg = $('#win-chart'); svg.replaceChildren(); const W = 760, H = 230, L = 40, B = 26, T = 28, K = 13;
  const a = item.exact.dist.slice(0, K), b = ref ? ref.exact.dist.slice(0, K) : [], max = Math.max(...a, ...b) * 1.05, gw = (W - L) / K, y = (v) => T + (H - T - B) * (1 - v / max);
  [0, 0.1, 0.2, 0.3].filter((v) => v <= max).forEach((v) => { put(svg, svgEl('line', { x1: L, x2: W, y1: y(v), y2: y(v), stroke: C.grid })); put(svg, svgEl('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end' })).textContent = Math.round(v * 100) + ' %'; });
  const bar = (x, v, fill, label) => { const r = svgEl('rect', { x, y: y(v), width: gw / 2 - 5, height: y(0) - y(v), rx: 3, fill }); r.append(svgEl('title')); r.firstChild.textContent = label; svg.append(r); };
  a.forEach((v, k) => { bar(L + k * gw + 3, v, C.obs, `${item.id} : ${k} gagnantes, ${pct(v, 2)}`); if (ref) bar(L + k * gw + gw / 2 + 2, b[k], C.th, `RANDOM_001 : ${k} gagnantes, ${pct(b[k], 2)}`); put(svg, svgEl('text', { x: L + (k + 0.5) * gw, y: H - 8, 'text-anchor': 'middle' })).textContent = k === K - 1 ? k + '+' : k; });
  const lg = [[item.id, C.obs], ['RANDOM_001', C.th]]; lg.forEach(([t, c], i) => { put(svg, svgEl('rect', { x: L + i * 170, y: 4, width: 10, height: 10, rx: 2, fill: c })); put(svg, svgEl('text', { x: L + 14 + i * 170, y: 13 })).textContent = t; });
  $('#win-caption').textContent = `E[gagnantes] = ${item.exact.mean.toFixed(4).replace('.', ',')} (${item.exact.mean_fraction}) pour ${item.id} comme pour RANDOM_001. P(au moins une gagnante) : ${pct(item.exact.p_ge1)} contre ${ref ? pct(ref.exact.p_ge1) : '—'}. P(au moins deux) : ${pct(item.exact.p_ge2)} contre ${ref ? pct(ref.exact.p_ge2) : '—'}.`;
}
function renderGeoTable(ctx) {
  const gen = ctx.data.portfolios.find((g) => g.game === 'euromillions'); if (!gen) return;
  const rows = gen.items.slice().sort((a, b) => b.exact.p_ge1 - a.exact.p_ge1);
  $('#em-table tbody').replaceChildren(...rows.map((it) => { const tr = el('tr', { 'data-id': it.id }, ...[it.id, it.family, it.exact.mean.toFixed(4).replace('.', ','), pct(it.exact.p_ge1, 2), pct(it.exact.p_ge2, 2), it.geometry.union, it.geometry.overlap_max, nb(it.geometry.coverage['2'].collisions), nb(it.geometry.coverage['3'].covered)].map((v) => el('td', { text: String(v) }))); tr.addEventListener('click', () => { $('#geo-select').value = it.id; renderGeo(ctx); }); return tr; }));
}
function setupGeo(data) {
  const ctx = { data, gen: null };
  const names = { euromillions: 'EuroMillions', loto: 'Loto', keno: 'Keno' };
  const pick = (game) => {
    ctx.gen = data.portfolios.find((g) => g.game === game);
    document.querySelectorAll('#geo-games button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.game === game)));
    $('#geo-select').replaceChildren(...ctx.gen.items.map((it) => el('option', { value: it.id, text: `${it.id} · ${it.family}` })));
    const fam = Object.entries(ctx.gen.catalog_families || {}).map(([k, v]) => `${k} ${v}`).join(' · ');
    $('#geo-gen').textContent = `${ctx.gen.label}. Affichés : ${ctx.gen.items.length} portefeuilles (${ctx.gen.shown}) de ${ctx.gen.grids_per_portfolio} grilles, sur ${ctx.gen.catalog_total} au catalogue${fam ? ' — familles : ' + fam : ''}.`;
    const def = ctx.gen.items.find((x) => x.id === 'LOW_OVERLAP_003') || ctx.gen.items.find((x) => x.family === 'BALANCED') || ctx.gen.items[0];
    $('#geo-select').value = def.id; renderGeo(ctx);
  };
  $('#geo-games').replaceChildren(...data.portfolios.map((g) => { const b = el('button', { 'data-game': g.game, 'aria-pressed': 'false' }, `${names[g.game] || g.game} · ${g.items.length}`, el('span', { class: 'badge-gen', text: 'GÉN. ' + g.generation })); b.addEventListener('click', () => pick(g.game)); return b; }));
  $('#geo-select').addEventListener('change', () => renderGeo(ctx));
  renderGeoTable(ctx); pick(data.portfolios[0].game);
}

// ------------------------------------------------------------ Lab
function renderLab(laws, mid) {
  const m0 = laws.metrics[mid], svg = $('#lab-chart'); svg.replaceChildren();
  const k = m0.values.length > 60 ? Math.ceil(m0.values.length / 45) : 1;
  const m = k === 1 ? m0 : Object.assign({}, m0, { values: [], p: [], observed: [] });
  if (k > 1) for (let i = 0; i < m0.values.length; i += k) { const j = Math.min(i + k, m0.values.length); m.values.push(m0.values[i] + '–' + m0.values[j - 1]); m.p.push(m0.p.slice(i, j).reduce((a, b) => a + b, 0)); m.observed.push(m0.observed.slice(i, j).reduce((a, b) => a + b, 0)); }
  const W = 560, H = 240, L = 44, B = 30, T = 30, n = m.values.length, obsP = m.observed.map((o) => o / m.n), max = Math.max(...m.p, ...obsP) * 1.08, y = (v) => T + (H - T - B) * (1 - v / max), bw = (W - L) / n;
  const ticks = [0, max / 2, max / 1.08].map((v) => Math.round(v * 1000) / 1000);
  ticks.forEach((v) => { put(svg, svgEl('line', { x1: L, x2: W, y1: y(v), y2: y(v), stroke: C.grid })); put(svg, svgEl('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end' })).textContent = pct(v, v < 0.1 ? 1 : 0); });
  m.p.forEach((p, i) => { const r = svgEl('rect', { x: L + i * bw + (bw > 4 ? 1 : 0), y: y(p), width: Math.max(bw - (bw > 4 ? 2 : 0), 0.8), height: y(0) - y(p), rx: bw > 8 ? 2 : 0, fill: '#b7d3f6' }); r.append(svgEl('title')); r.firstChild.textContent = `${m.values[i]} : loi exacte ${pct(p, 2)}, observé ${pct(obsP[i], 2)} (${m.observed[i]} tirages)`; svg.append(r); });
  const pts = obsP.map((p, i) => `${L + (i + 0.5) * bw},${y(p)}`).join(' ');
  put(svg, svgEl('polyline', { points: pts, fill: 'none', stroke: C.obs, 'stroke-width': 2, 'stroke-linejoin': 'round' }));
  if (n <= 30) obsP.forEach((p, i) => put(svg, svgEl('circle', { cx: L + (i + 0.5) * bw, cy: y(p), r: 4, fill: C.obs, stroke: '#fff', 'stroke-width': 2 })));
  const step = Math.ceil(n / 12); m.values.forEach((v, i) => { if (i % step === 0) put(svg, svgEl('text', { x: L + (i + 0.5) * bw, y: H - 10, 'text-anchor': 'middle' })).textContent = String(v).split('–')[0].replace(/\.0$/, '').replace('.', ',').slice(0, 9); });
  put(svg, svgEl('text', { x: L, y: 14, class: 'title' })).textContent = `${m.label} : loi exacte (barres) et historique (ligne), ${nb(m.n)} tirages` + (k > 1 ? `, classes regroupées par ${k}` : '');
  const note = m.sd_th !== undefined ? `Moyenne exacte ${m.mean_th.toFixed(2).replace('.', ',')}, observée ${m.mean_obs.toFixed(2).replace('.', ',')} · écart-type exact ${m.sd_th.toFixed(2).replace('.', ',')}, observé ${m.sd_obs.toFixed(2).replace('.', ',')}. ` : '';
  $('#lab-note').textContent = note + `χ² ${m.chi2.toFixed(1).replace('.', ',')} pour ${m.df} ddl · ${laws.monte_carlo_histories} historiques simulés · ${laws.tests} tests corrigés.` + (m.era_from ? ` Étoiles : tirages depuis le ${dateFr(m.era_from)} (règle à 12 étoiles).` : '');
  document.querySelectorAll('#lab-table tbody tr').forEach((tr) => tr.classList.toggle('sel', tr.dataset.id === mid));
}
function setupLab(laws) {
  const rows = Object.entries(laws.metrics).map(([id, m]) => ({ id, m, pmin: Math.min(m.p_chi2, m.p_mean ?? 1, m.p_sd ?? 1), q: Math.min(m.q_chi2 ?? 1, m.q_mean ?? 1, m.q_sd ?? 1) })).sort((a, b) => a.pmin - b.pmin);
  $('#lab-table tbody').replaceChildren(...rows.map(({ id, m, q }) => { const cell = (p) => { const td = el('td', { text: p === undefined ? '—' : fmtP(p) }); if (p !== undefined && p < 0.05) td.className = 'flag'; return td; }; const tr = el('tr', { 'data-id': id }, el('td', { text: (id.startsWith('stars') ? '★ ' : '') + m.label }), cell(m.p_chi2), cell(m.p_mean), cell(m.p_sd), el('td', { text: fmtP(q) })); tr.addEventListener('click', () => renderLab(laws, id)); return tr; }));
  renderLab(laws, rows[0].id);
}

// ------------------------------------------------------------ démarrage
function selectDraw(row, ctx, sel, dateInput) {
  renderDraw(row, ctx);
  sel.value = row[0];
  dateInput.value = row[1];
}
function nearestRow(rows, iso) {
  // rows triés par date croissante ; renvoie le tirage à cette date ou, sinon, le plus proche avant (ou à défaut après).
  let before = null, after = null;
  for (const r of rows) {
    if (r[1] === iso) return r;
    if (r[1] < iso) before = r; else { after = r; break; }
  }
  return before || after;
}
Promise.all([load('draws.json'), load('laws.json'), load('atlas.json'), load('manifest.json')]).then(([draws, laws, atlas, manifest]) => {
  const ctx = { draws, laws, rows: draws.rows };
  const sel = $('#draw-select');
  const byYear = new Map();
  draws.rows.forEach((r) => { const y = r[1].slice(0, 4); if (!byYear.has(y)) byYear.set(y, []); byYear.get(y).push(r); });
  sel.replaceChildren(...[...byYear.keys()].sort((a, b) => b - a).map((y) => {
    const group = el('optgroup', { label: y });
    group.append(...byYear.get(y).slice().reverse().map((r) => el('option', { value: r[0], text: `${dateFr(r[1])} · ${r[3].join(' ')} ★ ${r[4].join(' ')}` })));
    return group;
  }));
  const dateInput = $('#draw-date');
  dateInput.min = draws.rows[0][1]; dateInput.max = draws.rows[draws.rows.length - 1][1];
  sel.addEventListener('change', () => selectDraw(draws.rows.find((r) => r[0] === sel.value), ctx, sel, dateInput));
  dateInput.addEventListener('change', () => { if (!dateInput.value) return; const row = nearestRow(draws.rows, dateInput.value); if (row) selectDraw(row, ctx, sel, dateInput); });
  const hash = location.hash.match(/^#(EM-\d+)$/); const start = hash ? draws.rows.find((r) => r[0] === hash[1]) : null;
  selectDraw(start || draws.rows[draws.rows.length - 1], ctx, sel, dateInput);
  $('#data-provenance').textContent = `Données : ${nb(manifest.draws)} tirages FDJ du ${dateFr(manifest.first)} au ${dateFr(manifest.last)} · moteur ${manifest.engine} · base ${manifest.history_db_sha256.slice(0, 12)}…`;
  renderCooc(atlas); setupGeo(atlas); setupLab(laws);
}).catch((e) => { console.error(e); ['#draw-metrics', '#cooc-stats', '#geo-stats', '#lab-note'].forEach((s) => { const n = $(s); if (n) n.textContent = 'Les données n’ont pas pu être chargées. Lance engine/build_data.py puis actualise la page.'; }); });
