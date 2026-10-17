// Cloudflare Pages runs this in front of every request (a _worker.js in the upload folder).
// Everything is passed straight through, except the Letters game's files (/letters/...): those only go to a browser
// that has opened the private access link once,
//     https://learn.mikeohalloran.au/?for=<name>&letters=<key>
// which gives that browser a pass for 400 days (renewed on every visit). ?letters=off takes the pass away.
// The page hides the Letters tile unless the pass is there (mb_letters_ok). The key is filled in by build_site.py
// from learn_key.txt, which stays on the laptop and out of the repo.
const KEY = '__LETTERS_KEY__';
const AGE = 400 * 24 * 3600;       // the longest a browser keeps a cookie
const PASS = [
  `mb_letters=${KEY}; Max-Age=${AGE}; Path=/; Secure; HttpOnly; SameSite=Lax`,
  `mb_letters_ok=1; Max-Age=${AGE}; Path=/; Secure; SameSite=Lax`,
];
const CLEAR = [
  'mb_letters=; Max-Age=0; Path=/; Secure; HttpOnly; SameSite=Lax',
  'mb_letters_ok=; Max-Age=0; Path=/; Secure; SameSite=Lax',
];

function hasPass(request) {
  const cookie = request.headers.get('Cookie') || '';
  return cookie.split(/;\s*/).includes('mb_letters=' + KEY);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const given = url.searchParams.get('letters');
    if (given !== null) {                                   // the secret link (or ?letters=off)
      url.searchParams.delete('letters');
      const ok = given === KEY;
      const headers = new Headers({ Location: url.pathname + url.search + (ok ? '#letters' : ''), 'Cache-Control': 'no-store' });
      for (const c of ok ? PASS : given === 'off' ? CLEAR : []) headers.append('Set-Cookie', c);
      return new Response(null, { status: 302, headers });
    }
    const allowed = hasPass(request);
    let path;
    try { path = decodeURIComponent(url.pathname).replace(/\/+/g, '/').toLowerCase(); }
    catch (e) { return new Response('Bad request', { status: 400 }); }
    if (path.startsWith('/letters/') || path === '/letters') {
      if (!allowed) return new Response('Not found', { status: 404, headers: { 'Cache-Control': 'no-store' } });
      const res = await env.ASSETS.fetch(request);
      const out = new Response(res.body, res);
      out.headers.set('Cache-Control', 'private, max-age=86400');
      return out;
    }
    const res = await env.ASSETS.fetch(request);
    if (allowed && (res.headers.get('Content-Type') || '').includes('text/html')) {   // keep the pass fresh
      const out = new Response(res.body, res);
      for (const c of PASS) out.headers.append('Set-Cookie', c);
      return out;
    }
    return res;
  },
};
