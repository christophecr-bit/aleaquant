// Reference Cloudflare Worker: bind ASSETS to a directory containing /keno/index.json
// and /keno/keno-YYYY-MM.json. Configure run_worker_first for /tirages/keno/*.
const ORIGIN = 'https://aleaquant.aleaquant.workers.dev';
const ROUTE = /^\/tirages\/keno\/(KE-[A-Za-z0-9-]+)\/?$/;
let indexPromise;

function esc(value) {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

async function assetJson(env, path) {
  const response = await env.ASSETS.fetch(new Request(`${ORIGIN}/keno/${path}`));
  if (!response.ok) throw new Error(`asset ${path}: ${response.status}`);
  return response.json();
}

function notFound(method) {
  const body = '<!doctype html><html lang="fr"><meta charset="utf-8"><title>Tirage Keno introuvable | AleaQuant</title><h1>Tirage Keno introuvable</h1><p><a href="/tirages/">Voir les tirages</a></p></html>';
  return new Response(method === 'HEAD' ? null : body, {status: 404, headers: {
    'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'public, max-age=60',
    'X-Robots-Tag': 'noindex',
  }});
}

function page(draw) {
  const old = draw.rule === 'keno-70-20-v1';
  const formula = old ? '20 numéros parmi 70' : '16 numéros parmi 56';
  const title = `Tirage Keno du ${draw.date} — ${draw.id} | AleaQuant`;
  const description = `Résultat Keno ${draw.id} du ${draw.date}, ${formula}. Historique descriptif, sans prédiction.`;
  const canonical = `${ORIGIN}/tirages/keno/${encodeURIComponent(draw.id)}/`;
  const numberList = draw.main.map(n => `<li>${esc(n)}</li>`).join('');
  const structured = JSON.stringify({
    '@context': 'https://schema.org', '@type': 'Article', headline: title,
    datePublished: draw.date, description,
    author: {'@type': 'Organization', name: 'AleaQuant'},
  }).replace(/</g, '\\u003c');
  return `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${esc(title)}</title><meta name="description" content="${esc(description)}"><link rel="canonical" href="${esc(canonical)}"><meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(description)}"><meta property="og:url" content="${esc(canonical)}"><script type="application/ld+json">${structured}</script></head><body><main><p><a href="/tirages/">Tous les tirages</a></p><h1>Tirage Keno du ${esc(draw.date)}</h1><p>Identifiant ${esc(draw.id)} · ${formula}${draw.session ? ` · ${esc(draw.session)}` : ''}</p><ol>${numberList}</ol><p>Ces résultats décrivent un tirage passé. Ils ne prédisent pas les suivants.</p></main></body></html>`;
}

export default {
  async fetch(request, env) {
    const method = request.method;
    if (method !== 'GET' && method !== 'HEAD') return new Response(null, {status: 405, headers: {'Allow': 'GET, HEAD'}});
    const url = new URL(request.url);
    const match = ROUTE.exec(url.pathname);
    if (!match) return notFound(method);
    const id = match[1];
    try {
      // One index per isolate. A rejected fetch is retried on the next request.
      indexPromise ||= assetJson(env, 'index.json').catch(error => { indexPromise = undefined; throw error; });
      const index = await indexPromise;
      const month = index.id_to_month[id];
      if (!month) return notFound(method);
      const shard = await assetJson(env, `keno-${month}.json`);
      const draw = shard.draws.find(d => d.id === id);
      if (!draw) return notFound(method);
      const html = page(draw);
      return new Response(method === 'HEAD' ? null : html, {status: 200, headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'public, max-age=300, s-maxage=3600',
      }});
    } catch (error) {
      return new Response(method === 'HEAD' ? null : 'Service temporairement indisponible', {
        status: 503, headers: {'Content-Type': 'text/plain; charset=utf-8',
                               'Cache-Control': 'no-store'},
      });
    }
  },
};
