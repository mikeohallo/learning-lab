"""Screenshot check: draw the public pages at a phone width and a laptop width, and compare two versions of the site.

    python3 tools/test_screens.py shoot SITE_DIR OUT_DIR     draw every page of the site in SITE_DIR into OUT_DIR
    python3 tools/test_screens.py compare BASE_DIR NEW_DIR   compare two sets of drawings; prints same / CHANGED per page

Only the public pages are drawn: the games page and the six Numbers games, as a browser without the Letters pass
sees them. Nothing private is drawn, and this script prints words only (it never uploads a picture).
The same seed, a frozen clock and no animation make every drawing repeatable, so two drawings of the same code match.
The site has one theme (no dark mode), so each page is drawn once per width."""
import functools, http.server, socketserver, sys, threading
from pathlib import Path

PAGES = {'home': '', 'count': '#count', 'quick': '#quick', 'feed': '#feed', 'more': '#more', 'train': '#train', 'jump': '#jump'}
SIZES = {'phone': (390, 844), 'laptop': (1280, 800)}

# the same "random" numbers every time, so the games deal the same rounds
SEED = """(() => { let s = 1234567;
  Math.random = () => { s |= 0; s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const fake = { speak(u) { setTimeout(() => u.onend && u.onend(), 40); }, cancel() {}, getVoices() { return []; }, addEventListener() {} };
  Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true }); })();"""
STILL = '*,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;transition:none!important;caret-color:transparent!important}'


def shoot(site, out):
    from playwright.sync_api import sync_playwright
    site, out = Path(site).resolve(), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    socketserver.TCPServer.allow_reuse_address = True
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_address[1]}/index.html'
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for size, (w, h) in SIZES.items():
            for name, hash_ in PAGES.items():
                ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1,
                                    is_mobile=size == 'phone', has_touch=size == 'phone')
                ctx.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=''))
                ctx.route('https://fonts.gstatic.com/**', lambda r: r.abort())
                ctx.route('**/numbers/voices/index.json', lambda r: r.fulfill(status=200, content_type='application/json', body='{"clips":[]}'))
                ctx.route('**/letters/**', lambda r: r.fulfill(status=404, body=''))     # as a browser without the pass
                ctx.add_init_script(SEED)
                p = ctx.new_page()
                p.clock.install(time=1767225600000)          # 1 Jan 2026, the same every run
                p.goto(base + hash_)
                p.add_style_tag(content=STILL)
                p.clock.run_for(4000)                        # let the opening of each game play out
                p.evaluate('document.fonts.ready')
                p.screenshot(path=str(out / f'{name}-{size}.png'), full_page=True)
                ctx.close()
        b.close()
    srv.shutdown()
    print(f'drew {len(PAGES) * len(SIZES)} pages')


def compare(a, b):
    from PIL import Image, ImageChops
    a, b = Path(a), Path(b)
    names = sorted({p.name for p in a.glob('*.png')} | {p.name for p in b.glob('*.png')})
    changed = []
    for n in names:
        pa, pb = a / n, b / n
        if not pa.exists() or not pb.exists():
            print(f'CHANGED {n[:-4]}: {"new page" if not pa.exists() else "page gone"}'); changed.append(n); continue
        ia, ib = Image.open(pa).convert('RGB'), Image.open(pb).convert('RGB')
        if ia.size != ib.size:
            print(f'CHANGED {n[:-4]}: size {ia.size[0]}x{ia.size[1]} -> {ib.size[0]}x{ib.size[1]}'); changed.append(n); continue
        bbox = ImageChops.difference(ia, ib).getbbox()
        if bbox:
            print(f'CHANGED {n[:-4]}: differs in the area {bbox}'); changed.append(n)
        else:
            print(f'same    {n[:-4]}')
    print(f'{len(names) - len(changed)} of {len(names)} the same')
    return 1 if changed else 0


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'shoot':
        shoot(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == 'compare':
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    else:
        sys.exit(__doc__)
