"""Play Monster count and Quick look at phone, folding-phone and laptop sizes, check the narrator's three paths
(recorded clips, the browser's own voice, words only when muted), and run the voice maker against a fake API.
    python3 tools/test_numbers.py OUTDIR"""
import http.server, socketserver, sys, threading, functools, json, re, subprocess, tempfile, time, os
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent          # the repo root, where index.html lives
ROOT = Path(__file__).resolve().parent.parent
NUMBERS = next((d for d in (ROOT / 'numbers', ROOT / 'tools' / 'numbers') if (d / 'number_lines.json').exists()), ROOT / 'numbers')   # the narrator's tools
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
socketserver.TCPServer.allow_reuse_address = True
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
PORT = 8795
srv = socketserver.TCPServer(('127.0.0.1', PORT), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{PORT}/index.html'
css = ("@font-face{font-family:'Fredoka';font-weight:300 700;src:url(http://127.0.0.1:%d/Fredoka.ttf)}"
       "@font-face{font-family:'Nunito';font-weight:200 1000;src:url(http://127.0.0.1:%d/Nunito.ttf)}") % (PORT, PORT)
problems = []
def check(label, ok):
    print(('ok   ' if ok else 'FAIL ') + label)
    if not ok: problems.append(label)

# the browser's own voice, replaced by one that writes down what it was asked to say
FAKE_SPEECH = """(() => { window.__said = [];
  const fake = { speak(u) { window.__said.push(u.text); setTimeout(() => u.onend && u.onend(), 40); }, cancel() {},
                 getVoices() { return []; }, addEventListener() {} };
  Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true }); })();"""
LINES = {l['id']: l['text'] for l in json.loads((NUMBERS / 'number_lines.json').read_text())['lines']} if (NUMBERS / 'number_lines.json').exists() else None

def page_at(b, w, h, touch=True, clips=None):
    ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=touch, has_touch=touch)
    ctx.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=css))
    ctx.route('https://fonts.gstatic.com/**', lambda r: r.abort())
    if clips is None:              # no clips: the browser's voice says everything (so the fake can write it down)
        ctx.route('**/numbers/voices/index.json', lambda r: r.fulfill(status=200, content_type='application/json', body='{"clips":[]}'))
    elif clips == 'real':          # the narrator's real clips, as they are in site/numbers/voices
        pass
    else:                          # pretend the narrator's clips are there: every line, played from one small test file
        ctx.route('**/numbers/voices/index.json', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps({'clips': clips[0]})))
        ctx.route('**/numbers/voices/*.mp3', lambda r: (clips[1].append(r.request.url.rsplit('/', 1)[1]), r.fulfill(status=200, content_type='audio/mpeg', body=clips[2]))[1])
    ctx.add_init_script(FAKE_SPEECH)
    p = ctx.new_page()
    p.on('console', lambda m: m.type == 'error' and 'numbers/voices/index.json' not in m.text and '404' not in m.text and problems.append(f'console error: {m.text}'))
    p.on('pageerror', lambda e: problems.append(f'page error: {e}'))
    return ctx, p

def said(p): return p.evaluate('window.__said')

def count_all(p):
    """Tap every monster once, in page order."""
    n = p.evaluate('NC.want')
    for i in range(n):
        p.click(f'#cField .cmon >> nth={i}')
    return n

def tile(p, box, v): return f'#{box} .ntile[data-n="{v}"]'

def overlap_report(p, sel, box_sel):
    """Do the monsters overlap each other or stick out of their box? (on-screen boxes, 2 px slack)"""
    return p.evaluate(f"""(() => {{ const box = document.querySelector('{box_sel}').getBoundingClientRect();
      const r = [...document.querySelectorAll('{sel}')].map(e => e.getBoundingClientRect());
      let over = 0, out = 0, min = 1e9;
      r.forEach((a, i) => {{ min = Math.min(min, a.width);
        if (a.left < box.left - 2 || a.right > box.right + 2 || a.top < box.top - 2 || a.bottom > box.bottom + 2) out++;
        r.slice(i + 1).forEach(b => {{ const ax = a.left + a.width / 2, ay = a.top + a.height / 2, bx = b.left + b.width / 2, by = b.top + b.height / 2;
          if (Math.hypot(ax - bx, ay - by) < Math.min(a.width, b.width) * .92) over++; }}); }});
      return {{ n: r.length, over, out, min: Math.round(min) }}; }})()""")

with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ---------------------------------------------------------------- the lines the games use are all in the list
    src = (SITE / 'index.html').read_text(encoding='utf-8')
    m = re.search(r'/\*NUM_LINES\*/(.*?)/\*/NUM_LINES\*/', src, re.S)
    page_lines = json.loads(m.group(1)) if m else {}
    js = src[src.index('// ------------------------------------------------------------- numbers ---'):src.index('function buildNumbers()')]
    used = set(re.findall(r"'((?:c|q|p)_[a-z_]+|try_again)'", js))
    check(f'every line the games say is in the list ({len(used)} lines used, {len(page_lines)} in the page)', used <= set(page_lines) and len(page_lines) >= 32)
    check('the numbers one to twenty are all there', all(f'n_{i}' in page_lines for i in range(1, 21)))
    if LINES: check('the page has the same lines as number_lines.json', page_lines == LINES)

    # ---------------------------------------------------------------- the games page
    ctx, p = page_at(b, 390, 844)
    p.goto(BASE); p.wait_for_timeout(500)
    check('the Learning Lab opens on its games: 3, with Letters and Numbers headings', p.eval_on_selector_all('.gametile', 'e => e.length') == 3 and p.is_visible('#numbersHead') and p.is_visible('#home'))
    order = p.eval_on_selector_all('.gamelist > *', 'e => e.map(x => x.id)')
    check(f'Letters first, then Numbers ({", ".join(order)})', order.index('lettersHead') < order.index('playLetters') < order.index('numbersHead') < order.index('playCount') < order.index('playQuick'))
    p.screenshot(path=OUT / 'n0_games.png', full_page=True)

    # ---------------------------------------------------------------- Monster count, Easy, phone
    p.click('#playCount'); p.wait_for_function("NC.want > 0 && document.querySelectorAll('#cField .cmon').length === NC.want", timeout=5000)
    check('Monster count opens #count with 3 levels, Easy first, 5 dots', p.evaluate('location.hash') == '#count' and p.eval_on_selector_all('#cLevels .level', 'e => e.length') == 3
          and p.get_attribute('#cLevels .level >> nth=0', 'aria-pressed') == 'true' and p.eval_on_selector_all('#cDots i', 'e => e.length') == 5)
    q = p.evaluate('NC.queue')
    check(f'an Easy round counts 5 different amounts from 1 to 5 ({q})', sorted(q) == [1, 2, 3, 4, 5])
    p.wait_for_function("window.__said.length > 0", timeout=4000)
    check(f'it starts by saying what to do ("{said(p)[0]}")', said(p)[0] == page_lines['c_start'])
    o = overlap_report(p, '#cField .cmon', '#cField')
    check(f'Easy: {o["n"]} monsters, none overlapping, all inside, each {o["min"]} px', o['over'] == 0 and o['out'] == 0 and o['min'] >= 64)
    p.screenshot(path=OUT / 'n1_count.png')
    # a tap straight after a new question still gets its "one": the opening prompt doesn't talk over her
    p.evaluate("NC.queue[0] = 2; NC.n = 0; countNext()"); p.wait_for_timeout(60); p.click('#cField .cmon >> nth=0'); p.wait_for_timeout(600)
    check('tapping straight away: the "let\'s count" prompt doesn\'t talk over her "one"', said(p)[-1] == 'one')
    # make the first question a 4, so counting has something to do
    p.evaluate("NC.queue[0] = 4; NC.n = 0; countNext()"); p.wait_for_timeout(700)
    p.click('#cField .cmon >> nth=0'); p.wait_for_timeout(150)
    check('tapping a monster counts it: badge 1, "one"', p.text_content('#cField .cmon >> nth=0') == '1' and said(p)[-1] == 'one' and 'done' in p.get_attribute('#cField .cmon >> nth=0', 'class'))
    p.click('#cField .cmon >> nth=0'); p.wait_for_timeout(150)
    check('tapping it again doesn\'t count it twice', p.evaluate('NC.k') == 1 and 'again' in p.get_attribute('#cField .cmon >> nth=0', 'class'))
    check('the number choices wait until every monster is counted', p.is_hidden('#cTiles'))
    for i in (1, 2, 3): p.click(f'#cField .cmon >> nth={i}')
    p.wait_for_timeout(250)
    nums = p.eval_on_selector_all('#cTiles .ntile', 'e => e.map(x => +x.dataset.n)')
    check(f'after the last one: "How many monsters?" and three numbers in order ({nums})', p.is_visible('#cTiles') and 4 in nums and len(nums) == 3 and nums == sorted(nums))
    p.wait_for_function("window.__said.includes('How many monsters?')", timeout=3000)
    wrong = next(v for v in nums if v != 4)
    p.click(tile(p, 'cTiles', wrong)); p.wait_for_timeout(200)
    check('a wrong number shakes, the last badge (4) lights up, "Try again."', 'nope' in p.get_attribute(tile(p, 'cTiles', wrong), 'class') and p.evaluate('NC.n') == 0
          and 'hint' in p.get_attribute('#cField .cmon[data-k="4"] b', 'class') and said(p)[-1] == 'Try again.')
    p.screenshot(path=OUT / 'n2_count_answer.png')
    p.click(tile(p, 'cTiles', 4))
    p.wait_for_function('NC.n === 1', timeout=6000)
    check('the right number: "four", praise, then the next lot of monsters', 'four' in said(p) and p.eval_on_selector_all('#cDots i.miss', 'e => e.length') == 1)
    # the rest of the round
    for k in range(1, 5):
        p.wait_for_function(f"NC.n === {k} && !NC.busy && document.querySelectorAll('#cField .cmon').length === NC.want", timeout=6000)
        count_all(p); p.wait_for_timeout(120)
        p.click(tile(p, 'cTiles', p.evaluate('NC.want')))
    p.wait_for_function("!document.getElementById('cEnd').hidden", timeout=8000)
    check(f'end of the round: "{p.text_content("#cEndWord")}", 4 green dots and 1 pink', p.text_content('#cEndWord') == 'Great counting!'
          and p.eval_on_selector_all('#cEndDots i.hit', 'e => e.length') == 4 and p.eval_on_selector_all('#cEndDots i.miss', 'e => e.length') == 1)
    p.wait_for_function("window.__said.includes('Great counting!')", timeout=3000)
    check('the end screen says it once (the big words, not the spoken-words line as well)', not p.evaluate("$('cSay').classList.contains('show')"))
    p.screenshot(path=OUT / 'n3_count_end.png')
    p.click('#cAgain'); p.wait_for_timeout(300)
    check('Play again starts a new round', p.is_hidden('#cEnd') and p.evaluate('NC.n') == 0 and p.is_visible('#cField'))
    # Medium and Tricky
    p.click('#cLevels .level >> nth=1'); p.wait_for_timeout(300)
    q = p.evaluate('NC.queue')
    check(f'Medium: amounts from 4 to 10 ({q})', all(4 <= v <= 10 for v in q) and len(set(q)) == 5)
    p.click('#cLevels .level >> nth=2'); p.wait_for_timeout(300)
    q = p.evaluate('NC.queue')
    check(f'Tricky: amounts from 8 to 20 ({q})', all(8 <= v <= 20 for v in q) and len(set(q)) == 5)
    ctx.close()

    # every amount at every size: never overlapping, never off the field, big enough to tap
    for (w, h, name) in ((360, 740, 'small phone'), (390, 844, 'phone'), (904, 1000, 'folding phone open'), (1280, 800, 'laptop')):
        ctx, p = page_at(b, w, h, touch=w < 1000)
        p.goto(BASE + '#count'); p.wait_for_function("document.querySelectorAll('#cField .cmon').length > 0", timeout=5000)
        r = p.evaluate("""(() => { const W = $('cField').clientWidth - 18, out = [];
          for (let n = 1; n <= 20; n++) { let worst = 1e9, size = 1e9, outside = 0;
            const H = countHeight(n, W + 18) - 18;
            for (let t = 0; t < 60; t++) { const { m, spots } = countLayout(n, W, H); size = Math.min(size, m);
              spots.forEach(([x, y], i) => { if (x < m / 2 - 1 || x > W - m / 2 + 1 || y < m / 2 - 1 || y > H - m / 2 + 1) outside++;
                spots.slice(i + 1).forEach(([a, b]) => worst = Math.min(worst, Math.hypot(a - x, b - y) / m)); }); }
            out.push({ n, m: size, gap: n > 1 ? +worst.toFixed(2) : 9, outside }); }
          return out; })()""")
        bad = [x for x in r if x['gap'] < 1 or x['outside']]
        small = min(x['m'] for x in r if x['n'] <= 10), min(x['m'] for x in r)
        check(f'{name} {w}px: 1 to 20 monsters x 60 layouts, none overlapping or off the field; smallest {small[0]} px up to 10, {small[1]} px at 20{": " + str(bad[:3]) if bad else ""}',
              not bad and small[0] >= 56 and small[1] >= 44)
        # count 20 for real: the numbers come into view at the end
        p.evaluate("NC.level = '3'; NC.queue = [20, 12, 9, 15, 8]; NC.n = 0; countNext()"); p.wait_for_timeout(200)
        o = overlap_report(p, '#cField .cmon', '#cField')
        count_all(p); p.wait_for_timeout(900)
        tb = p.evaluate("$('cTiles').getBoundingClientRect().bottom")
        cut = p.evaluate("(() => { const f = $('cField').getBoundingClientRect(); return [...document.querySelectorAll('#cField .cmon b')].filter(e => { const r = e.getBoundingClientRect(); return r.left < f.left || r.right > f.right || r.top < f.top || r.bottom > f.bottom; }).length; })()")
        check(f'{name}: 20 monsters on screen ({o["min"]} px, {o["over"]} overlapping), every number badge whole ({cut} cut off), the numbers in view after counting',
              o['n'] == 20 and o['over'] == 0 and o['out'] == 0 and cut == 0 and tb <= h + 1)
        if w == 360: p.screenshot(path=OUT / 'n4_count20_small.png', full_page=True)
        ctx.close()

    # ---------------------------------------------------------------- Quick look, phone
    ctx, p = page_at(b, 390, 844)
    p.goto(BASE); p.wait_for_timeout(400)
    p.click('#playQuick'); p.wait_for_function('NQ.want > 0', timeout=5000)
    check('Quick look opens #quick with 3 levels and 8 dots', p.evaluate('location.hash') == '#quick' and p.eval_on_selector_all('#qLevels .level', 'e => e.length') == 3
          and p.eval_on_selector_all('#qDots i', 'e => e.length') == 8)
    q = p.evaluate('NQ.queue')
    check(f'an Easy round: 8 amounts from 1 to 5, every one at least once, no two the same in a row ({q})', len(q) == 8 and set(q) == {1, 2, 3, 4, 5} and all(a != b for a, b in zip(q, q[1:])))
    check('the monsters start hidden', 'hide' in p.get_attribute('#qCard', 'class'))
    p.wait_for_function("!document.getElementById('qCard').classList.contains('hide')", timeout=5000)
    check(f'"Quick look!", then they pop up: {p.evaluate("NQ.want")} of the same monster', said(p)[:1] == ['Quick look!']
          and p.eval_on_selector_all('#qMons .qmon', 'e => e.length') == p.evaluate('NQ.want') and len(set(p.eval_on_selector_all('#qMons .qmon', 'e => e.map(x => x.src)'))) == 1)
    p.wait_for_timeout(500)
    o = overlap_report(p, '#qMons .qmon', '#qCard')
    check(f'Quick look: none overlapping, all on the card, each {o["min"]} px', o['over'] == 0 and o['out'] == 0 and o['min'] >= 40)
    p.screenshot(path=OUT / 'n5_quick_show.png')
    p.wait_for_function("document.getElementById('qCard').classList.contains('hide')", timeout=4000)
    t_hide = time.time()
    p.wait_for_function("!document.getElementById('qTiles').hidden", timeout=2000)
    nums = p.eval_on_selector_all('#qTiles .ntile', 'e => e.map(x => +x.dataset.n)')
    want = p.evaluate('NQ.want')
    check(f'they hide, then "How many did you see?" and three numbers ({nums})', want in nums and len(nums) == 3 and p.is_visible('#qPeek'))
    p.wait_for_function("window.__said.includes('How many did you see?')", timeout=3000); p.wait_for_timeout(450)
    hidden_ok = p.evaluate("(() => { const c = $('qCard').getBoundingClientRect(); return [...document.querySelectorAll('#qMons .qmon')].every(e => e.getBoundingClientRect().top >= c.bottom - 1); })()")
    check('hidden means hidden: every monster is below the card', hidden_ok)
    p.screenshot(path=OUT / 'n6_quick_ask.png')
    p.click('#qPeek'); p.wait_for_timeout(150)
    check('Peek again shows them again', 'hide' not in p.get_attribute('#qCard', 'class') and p.is_hidden('#qPeek'))
    p.wait_for_function("document.getElementById('qCard').classList.contains('hide')", timeout=4000)
    wrong = next(v for v in nums if v != want)
    p.click(tile(p, 'qTiles', wrong)); p.wait_for_timeout(150)
    check('a wrong number shakes, "Have another look." and they pop up again', 'nope' in p.get_attribute(tile(p, 'qTiles', wrong), 'class'))
    p.wait_for_function("!document.getElementById('qCard').classList.contains('hide')", timeout=4000)
    check('  (said "Have another look.")', 'Have another look.' in said(p))
    p.click(tile(p, 'qTiles', want)); p.wait_for_timeout(200)
    check('the right number: they come out to check, and stay', 'hide' not in p.get_attribute('#qCard', 'class') and 'yes' in p.get_attribute(tile(p, 'qTiles', want), 'class'))
    p.wait_for_function('NQ.n === 1', timeout=6000)
    check('a peek or a wrong go makes a pink dot', p.eval_on_selector_all('#qDots i.miss', 'e => e.length') == 1)
    for k in range(1, 8):
        p.wait_for_function(f"NQ.n === {k} && !document.getElementById('qTiles').hidden && !NQ.busy", timeout=8000)
        p.click(tile(p, 'qTiles', p.evaluate('NQ.want')))
    p.wait_for_function("!document.getElementById('qEnd').hidden", timeout=8000)
    check(f'end of the round: "{p.text_content("#qEndWord")}", 7 green dots', p.text_content('#qEndWord') == 'Super sharp eyes!' and p.eval_on_selector_all('#qEndDots i.hit', 'e => e.length') == 7)
    p.screenshot(path=OUT / 'n7_quick_end.png')
    # the arrangements
    r = p.evaluate("""(() => { const bad = [];
      for (let n = 1; n <= 6; n++) for (let t = 0; t < 200; t++) { const s = scatterPts(n);
        if (s.length !== n) bad.push('count ' + n);
        s.forEach(([x, y], i) => { if (x < .14 || x > .86 || y < .14 || y > .86) bad.push('outside ' + n);
          s.slice(i + 1).forEach(([a, b]) => { if (Math.hypot(a - x, b - y) < .25) bad.push('touching ' + n); }); }); }
      for (let n = 1; n <= 6; n++) if (dicePts(n).length !== n) bad.push('dice ' + n);
      return [...new Set(bad)]; })()""")
    check(f'Mixed up: 1 to 6 x 200 arrangements, none touching or off the card{": " + str(r) if r else ""}', not r)
    p.click('#qLevels .level >> nth=2')
    for k in range(4):
        p.wait_for_function(f"NQ.n === {k} && !document.getElementById('qTiles').hidden && !NQ.busy", timeout=8000)
        g = p.evaluate("""(() => { const c = $('qCard').getBoundingClientRect(), mid = c.left + c.width / 2;
          const xs = [...document.querySelectorAll('#qMons .qmon')].map(e => { const r = e.getBoundingClientRect(); return r.left + r.width / 2; });
          return { want: NQ.want, left: xs.filter(x => x < mid).length, right: xs.filter(x => x >= mid).length, tiles: [...document.querySelectorAll('#qTiles .ntile')].length }; })()""")
        check(f'Two groups: {g["left"]} and {g["right"]} make {g["want"]}, with 4 numbers to pick from', 6 <= g['want'] <= 10 and g['left'] + g['right'] == g['want']
              and 1 <= g['left'] <= 5 and 1 <= g['right'] <= 5 and g['tiles'] == 4)
        if k == 0:
            p.click('#qPeek'); p.wait_for_timeout(400); p.screenshot(path=OUT / 'n8_quick_two.png')
            o = overlap_report(p, '#qMons .qmon', '#qCard')
            check(f'Two groups: none overlapping, all on the card, each {o["min"]} px', o['over'] == 0 and o['out'] == 0 and o['min'] >= 28)
            p.wait_for_function("document.getElementById('qCard').classList.contains('hide')", timeout=4000)
        p.click(tile(p, 'qTiles', p.evaluate('NQ.want')))
    p.click('#quickgame .back'); p.wait_for_timeout(300)
    check('All games stops the game (no timer left running)', p.evaluate('NQ.busy') is False and p.is_visible('#home') and p.evaluate('location.hash') == '')
    p.evaluate("location.hash = '#quick'"); p.wait_for_timeout(400)
    check('it remembers the level (Tricky)', p.get_attribute('#qLevels .level >> nth=2', 'aria-pressed') == 'true')
    ctx.close()

    # ---------------------------------------------------------------- the narrator's three ways of speaking
    test_mp3 = None
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / 'a.wav'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.25', str(wav)], check=True)
        mp3 = Path(td) / 'a.mp3'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(wav), '-b:a', '64k', str(mp3)], check=True)
        test_mp3 = mp3.read_bytes()
    fetched = []
    ctx, p = page_at(b, 390, 844, clips=(sorted(page_lines), fetched, test_mp3))
    p.goto(BASE + '#count'); p.wait_for_function("document.querySelectorAll('#cField .cmon').length > 0", timeout=5000)
    p.evaluate("NC.queue[0] = 3; NC.n = 0; countNext()"); p.wait_for_timeout(300)
    p.click('#cField .cmon >> nth=0'); p.wait_for_timeout(700)
    check(f'with the clips there, the game plays them ({", ".join(sorted(set(fetched))[:6])}...) and the browser voice stays quiet',
          'n_1.mp3' in fetched and said(p) == [])
    check('  and the words still show', p.text_content('#cSay') == 'one')
    ctx.close()
    real = SITE / 'numbers' / 'voices'
    idx = json.loads((real / 'index.json').read_text()) if (real / 'index.json').exists() else {'clips': []}
    if idx['clips']:
        missing = [i for i in page_lines if i not in idx['clips'] or not (real / f'{i}.mp3').exists()]
        check(f'the real narrator: {len(idx["clips"])} clips, one for every line{": missing " + str(missing) if missing else ""}', not missing)
        ctx, p = page_at(b, 390, 844, clips='real')
        got = []; p.on('response', lambda r: r.url.endswith('.mp3') and '/numbers/voices/' in r.url and got.append((r.url.rsplit('/', 1)[1], r.status)))
        p.goto(BASE + '#count'); p.wait_for_function("document.querySelectorAll('#cField .cmon').length > 0", timeout=5000)
        p.evaluate("NC.queue[0] = 2; NC.n = 0; countNext()"); p.wait_for_timeout(300)
        p.click('#cField .cmon >> nth=0'); p.wait_for_timeout(1500)
        ok = dict(got)
        check(f'the real clips load and play ({len(ok)} fetched, n_1 {ok.get("n_1.mp3")}), and the browser voice stays quiet', ok.get('n_1.mp3') == 200 and said(p) == [])
        ctx.close()
    ctx, p = page_at(b, 390, 844)
    p.goto(BASE + '#count'); p.wait_for_function("document.querySelectorAll('#cField .cmon').length > 0", timeout=5000)
    p.wait_for_timeout(800)
    p.click('#countgame .mute'); p.wait_for_timeout(100)
    n0 = len(said(p))
    p.evaluate("NC.queue[0] = 3; NC.n = 0; countNext()"); p.wait_for_timeout(200)
    p.click('#cField .cmon >> nth=0'); p.wait_for_timeout(600)
    check('muted: nothing is said out loud, the words show instead', len(said(p)) == n0 and p.text_content('#cSay') == 'one')
    p.click('#countgame .mute')
    ctx.close()

    # ---------------------------------------------------------------- other sizes
    for (w, h, name) in ((360, 740, 'small phone'), (904, 1000, 'folding phone open'), (1280, 800, 'laptop')):
        ctx, p = page_at(b, w, h, touch=w < 1000)
        for hsh in ('#count', '#quick', ''):
            p.goto(BASE + hsh); p.wait_for_timeout(700)
            check(f'{name} {w}px {hsh}: no sideways scroll', p.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        p.goto(BASE + '#quick'); p.wait_for_function("!document.getElementById('qTiles').hidden", timeout=6000)
        tw = p.evaluate("Math.min(...[...document.querySelectorAll('#qTiles .ntile')].map(e => e.getBoundingClientRect().width))")
        check(f'{name}: number tiles {tw:.0f} px (2 cm is about 76 px)', tw >= 76)
        if w == 904: p.screenshot(path=OUT / 'n9_quick_fold.png')
        ctx.close()
    b.close()

# ---------------------------------------------------------------- the voice maker, against a fake Google
if (NUMBERS / 'number_voices.py').exists():
    mock = Path(__file__).resolve().parent.parent / 'letters' / 'tests' / 'mock_gemini.py'
    mock = mock if mock.exists() else Path(__file__).resolve().parent / 'letters' / 'tests' / 'mock_gemini.py'
    if mock.exists():
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for f in ('number_voices.py', 'number_lines.json'): (td / f).write_bytes((NUMBERS / f).read_bytes())
            m = subprocess.Popen([sys.executable, str(mock), '8796', 'normal']); time.sleep(.8)
            env = {**os.environ, 'GEN_API_BASE': 'http://127.0.0.1:8796/v1beta', 'GEMINI_API_KEY': 'test-key', 'GEN_PACE': '0'}
            try:
                r = subprocess.run([sys.executable, 'number_voices.py'], cwd=td, env=env, capture_output=True, text=True, timeout=120)
                wavs = sorted(x.stem for x in (td / 'voices' / 'narrator').glob('*.wav'))
                check(f'voice maker: {len(wavs)} clips made in {(td / "voices" / "narrator" / "voice.txt").read_text().strip()}, and a listening page',
                      len(wavs) == len(LINES) and (td / 'listen.html').exists() and 'en-au-tutor-3' in (td / 'voices' / 'narrator' / 'voice.txt').read_text())
                r = subprocess.run([sys.executable, 'number_voices.py'], cwd=td, env=env, capture_output=True, text=True, timeout=60)
                check('running it again makes nothing new', 'already made' in r.stdout)
                r = subprocess.run([sys.executable, 'number_voices.py', 'redo', 'n_4'], cwd=td, env=env, capture_output=True, text=True, timeout=60)
                check('redo keeps the old take', len(list((td / 'voices' / '_old').glob('n_4.*.wav'))) == 1 and (td / 'voices' / 'narrator' / 'n_4.wav').exists())
                out = td / 'site_voices'
                subprocess.run([sys.executable, str(NUMBERS / 'make_number_voices.py'), str(td / 'voices' / 'narrator'), str(out)], capture_output=True, text=True, timeout=120)
                idx = json.loads((out / 'index.json').read_text())
                check(f'the clips become {len(idx["clips"])} MP3s and an index the game reads', sorted(idx['clips']) == sorted(LINES) and len(list(out.glob('*.mp3'))) == len(LINES))
                r = subprocess.run([sys.executable, 'number_voices.py'], cwd=td, env={**env, 'GEMINI_API_KEY': ''}, capture_output=True, text=True, timeout=30)
                check('without the key it says how to set it, and stops', r.returncode != 0 and 'setx GEMINI_API_KEY' in (r.stdout + r.stderr))
            finally:
                m.kill()

print('PROBLEMS:' if problems else 'no problems')
for x in problems: print('  ', x)
sys.exit(1 if problems else 0)
