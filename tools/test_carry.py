"""The one-time hand-over of Sam's progress from the monster site, where Letters and Numbers used to live.
Both sites are served under their real addresses inside the test browser (nothing goes online).
    python3 tools/test_carry.py MONSTER_SITE_DIR"""
import json, mimetypes, sys
from pathlib import Path
from urllib.parse import urlparse, unquote
from playwright.sync_api import sync_playwright

LEARN = Path(__file__).resolve().parent.parent          # the repo root, where index.html lives
if len(sys.argv) < 2: sys.exit(__doc__)
MONSTER = Path(sys.argv[1])           # the monster site's folder (index.html and its pictures)
problems = []
def check(label, ok):
    print(('ok   ' if ok else 'FAIL ') + label)
    if not ok: problems.append(label)

def serve(root):
    def handler(route):
        path = unquote(urlparse(route.request.url).path).lstrip('/') or 'index.html'
        f = root / path
        if f.is_file(): route.fulfill(status=200, body=f.read_bytes(), content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream')
        else: route.fulfill(status=404, body='not found')
    return handler

with sync_playwright() as pw:
    b = pw.chromium.launch()
    def fresh():
        ctx = b.new_context(viewport={'width': 390, 'height': 844})
        ctx.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=''))
        ctx.route('https://fonts.gstatic.com/**', lambda r: r.abort())
        ctx.route('https://learn.mikeohalloran.au/**', serve(LEARN))
        ctx.route('https://monsters.mikeohalloran.au/**', serve(MONSTER))
        ctx.add_cookies([{'name': 'mb_letters_ok', 'value': '1', 'domain': 'learn.mikeohalloran.au', 'path': '/'}])
        p = ctx.new_page(); trail = []
        def nav(f):   # page loads only: the address being tidied up afterwards (same page, same site) isn't a hop
            if f != p.main_frame: return
            if trail and urlparse(trail[-1]).hostname == urlparse(f.url).hostname and '#import=' in trail[-1]: trail[-1] = f.url; return
            trail.append(f.url)
        p.on('framenavigated', nav)
        p.on('pageerror', lambda e: problems.append(f'page error: {e}'))
        return ctx, p, trail
    ls = lambda p, k: p.evaluate(f"localStorage.getItem('{k}')")

    # Sam's phone: progress saved on the monster site from before
    ctx, p, trail = fresh()
    p.goto('https://monsters.mikeohalloran.au/?for=Sam'); p.wait_for_timeout(400)
    p.evaluate("""localStorage.setItem('monster-book.letters', JSON.stringify({ traced: { a: 1, b: 1, c: 1 }, next: 'd', mode: 'spell', level: '2', hlevel: '2' }));
                  localStorage.setItem('monster-book.numbers', JSON.stringify({ count: '2', quick: '3' }));
                  localStorage.setItem('monster-book.sound', 'off')""")
    trail.clear()
    p.goto('https://learn.mikeohalloran.au/?for=Sam#letters', wait_until='commit')
    p.wait_for_function("location.hostname === 'learn.mikeohalloran.au' && !location.hash.startsWith('#import') && document.readyState === 'complete' && typeof LS !== 'undefined'", timeout=8000)
    p.wait_for_timeout(500)
    hops = [urlparse(u).hostname + (urlparse(u).query and '?' + urlparse(u).query) for u in trail]
    check(f'first visit on Sam\'s phone: one hop to the monster site and back ({" -> ".join(hops)})',
          len(trail) == 3 and 'monsters.mikeohalloran.au/?handoff=learn' in trail[1] and trail[2].startswith('https://learn.mikeohalloran.au/?for=Sam'))
    lt = json.loads(ls(p, 'learning-lab.letters') or '{}')
    check(f'her Letters progress came across (next letter {lt.get("next")}, {len(lt.get("traced", {}))} traced, mode {lt.get("mode")})', lt.get('next') == 'd' and len(lt.get('traced', {})) == 3 and lt.get('mode') == 'spell')
    check('her Numbers levels and the mute setting came across', json.loads(ls(p, 'learning-lab.numbers') or '{}') == {'count': '2', 'quick': '3'} and ls(p, 'learning-lab.sound') == 'off')
    check(f'and she lands where she was going: {p.evaluate("location.hash")}, the Spell game open, the address tidy', p.evaluate('location.hash') == '#letters'
          and p.is_visible('#spellBox') and '#import' not in p.url)
    trail.clear()
    p.goto('https://learn.mikeohalloran.au/?for=Sam'); p.wait_for_timeout(800)
    check('the next visit stays put (no more hops)', all(urlparse(u).hostname == 'learn.mikeohalloran.au' for u in trail) and p.is_visible('#home'))
    p.evaluate("location.hash = '#import=' + encodeURIComponent(JSON.stringify({ letters: JSON.stringify({ next: 'z' }), sound: 'loud' }))"); p.reload(); p.wait_for_timeout(500)
    check('an import never overwrites what\'s there, and ignores nonsense', json.loads(ls(p, 'learning-lab.letters'))['next'] == 'd' and ls(p, 'learning-lab.sound') == 'off')
    ctx.close()

    # someone else's device: no hop
    ctx, p, trail = fresh()
    p.goto('https://learn.mikeohalloran.au/?for=Max'); p.wait_for_timeout(800)
    check('a gift copy (?for=Max) never hops to the monster site', all(urlparse(u).hostname == 'learn.mikeohalloran.au' for u in trail) and p.is_visible('#home'))
    ctx.close()

    # Sam's phone with nothing saved on the monster site: one hop, nothing breaks
    ctx, p, trail = fresh()
    p.goto('https://learn.mikeohalloran.au/?for=Sam', wait_until='commit')
    p.wait_for_function("location.hostname === 'learn.mikeohalloran.au' && !location.hash.startsWith('#import') && document.readyState === 'complete'", timeout=8000)
    p.wait_for_timeout(500)
    check(f'nothing to carry: back home after one hop ({len(trail)} pages), nothing made up', len(trail) == 3 and p.is_visible('#home') and ls(p, 'learning-lab.letters') is None)
    ctx.close()
    b.close()

print('PROBLEMS:' if problems else 'no problems')
for x in problems: print('  ', x)
sys.exit(1 if problems else 0)
