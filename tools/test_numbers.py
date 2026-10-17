"""Play Monster count, Quick look, Feed the monster, More or less, Monster train and Jump in the bed at phone, folding-phone and laptop sizes, check the narrator's three paths
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
LINES_N = {i: w for i, w in enumerate(['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'], 1)}

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
    used = set(re.findall(r"'((?:c|q|p|f|m|t|j)_[a-z_]+|try_again)'", js)) - {'f_want_', 'j_bed_', 'j_on_', 'j_off_'}
    check(f'every line the games say is in the list ({len(used)} lines used, {len(page_lines)} in the page)', used <= set(page_lines) and len(page_lines) >= 72)
    check('Jump in the bed has a line for one to ten on the bed, and for one to three jumping on and one or two rolling off',
          all(f'j_bed_{i}' in page_lines for i in range(1, 11)) and page_lines['j_bed_1'] == 'One monster on the bed.' and all(f'j_on_{i}' in page_lines for i in (1, 2, 3)) and all(f'j_off_{i}' in page_lines for i in (1, 2)))
    check('Feed the monster can ask for one to ten cookies, and says "cookie" for one', all(f'f_want_{i}' in page_lines for i in range(1, 11))
          and page_lines['f_want_1'].endswith(' one cookie.') and page_lines['f_want_10'].endswith(' ten cookies.'))
    check('the numbers one to twenty are all there', all(f'n_{i}' in page_lines for i in range(1, 21)))
    if LINES: check('the page has the same lines as number_lines.json', page_lines == LINES)

    # ---------------------------------------------------------------- the games page
    ctx, p = page_at(b, 390, 844)
    p.goto(BASE); p.wait_for_timeout(500)
    check('the Learning Lab opens on its games: 7, with Letters and Numbers headings', p.eval_on_selector_all('.gametile', 'e => e.length') == 7 and p.is_visible('#numbersHead') and p.is_visible('#home'))
    order = p.eval_on_selector_all('.gamelist > *', 'e => e.map(x => x.id)')
    check(f'Letters first, then Numbers ({", ".join(order)})', order.index('lettersHead') < order.index('playLetters') < order.index('numbersHead') < order.index('playCount')
          < order.index('playQuick') < order.index('playFeed') < order.index('playMore') < order.index('playTrain') < order.index('playJump'))
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

    # ---------------------------------------------------------------- Feed the monster, phone
    ctx, p = page_at(b, 390, 844)
    p.goto(BASE); p.wait_for_timeout(400)
    p.click('#playFeed'); p.wait_for_function('FD.want > 0', timeout=5000)
    check('Feed the monster opens #feed with 3 levels, Easy first, 5 dots', p.evaluate('location.hash') == '#feed' and p.eval_on_selector_all('#fLevels .level', 'e => e.length') == 3
          and p.get_attribute('#fLevels .level >> nth=0', 'aria-pressed') == 'true' and p.eval_on_selector_all('#fProg i', 'e => e.length') == 5)
    q = p.evaluate('FD.queue.map(x => x.want)')
    check(f'an Easy round asks for 5 different amounts from 1 to 5 ({q}), on an empty plate', sorted(q) == [1, 2, 3, 4, 5] and p.evaluate('FD.k') == 0
          and p.eval_on_selector_all('#fPlate .ck', 'e => e.length') == 0 and p.eval_on_selector_all('#fPlate .fslot', 'e => e.length') == 10)
    want = p.evaluate('FD.want')
    p.wait_for_function("window.__said.length >= 2", timeout=4000)
    check(f'it says what the monster wants, then what to do ({said(p)[:2]})', said(p)[:2] == [page_lines[f'f_want_{want}'], page_lines['f_tap']])
    check(f'the bubble shows the number and that many dots ({p.text_content("#fNum")})', p.text_content('#fNum') == str(want) and p.eval_on_selector_all('#fDots i', 'e => e.length') == want)
    p.screenshot(path=OUT / 'f1_feed.png')
    p.click('#fFeed'); p.wait_for_timeout(200)
    check('Feed with nothing on the plate: the jar wiggles, "Tap the jar..."', 'hint' in p.get_attribute('#fJar', 'class') and said(p)[-1] == page_lines['f_tap'] and p.evaluate('FD.tries') == 0)
    p.evaluate("FD.queue[0] = { want: 4, start: 0, dir: 0 }; FD.n = 0; feedNext()"); p.wait_for_timeout(500)
    for i in range(3): p.click('#fJar'); p.wait_for_timeout(120)
    check('tapping the jar puts a cookie on the plate each time, counting along ("three")', p.evaluate('FD.k') == 3 and p.eval_on_selector_all('#fPlate .ck', 'e => e.length') == 3 and said(p)[-1] == 'three')
    filled = p.eval_on_selector_all('#fPlate .fslot', 'e => e.map(x => !!x.querySelector(".ck"))')
    check('the plate is a ten frame and fills from the start', filled == [True] * 3 + [False] * 7)
    p.click('#fFeed'); p.wait_for_timeout(250)
    check('too few: the monster shakes, "Still hungry! Put some more on."', 'nope' in p.get_attribute('#fMon', 'class') and said(p)[-1] == page_lines['f_more'] and p.evaluate('FD.n') == 0)
    for i in range(2): p.click('#fJar'); p.wait_for_timeout(120)
    p.click('#fFeed'); p.wait_for_timeout(250)
    check('too many: "Oh no, too many! Take some away."', said(p)[-1] == page_lines['f_less'] and p.evaluate('FD.n') == 0 and p.evaluate('FD.tries') == 2)
    p.click('#fPlate .fslot >> nth=1'); p.wait_for_timeout(200)
    check('tapping a cookie takes one off ("four"), and the plate closes up', p.evaluate('FD.k') == 4 and said(p)[-1] == 'four'
          and p.eval_on_selector_all('#fPlate .fslot', 'e => e.map(x => !!x.querySelector(".ck"))') == [True] * 4 + [False] * 6)
    p.screenshot(path=OUT / 'f2_feed_four.png')
    p.click('#fFeed'); p.wait_for_timeout(300)
    check('just right: the cookies go to the monster', 'eat' in p.get_attribute('#fPlate', 'class') and p.evaluate('FD.busy'))
    p.click('#fJar'); p.wait_for_timeout(100)
    check('  (and the jar is shut while it eats)', p.evaluate('FD.k') == 4)
    p.wait_for_function("document.getElementById('fMon').classList.contains('chomp')", timeout=3000)
    p.wait_for_function('FD.n === 1', timeout=6000)
    check('it chomps, "Yum yum!" and "four", a pink dot (it took three goes), then the next monster',
          page_lines['f_yum'] in said(p) and said(p)[said(p).index(page_lines['f_yum']) + 1] == 'four' and p.eval_on_selector_all('#fProg i.miss', 'e => e.length') == 1
          and p.evaluate('FD.k') == 0 and p.eval_on_selector_all('#fPlate .ck', 'e => e.length') == 0)
    p.evaluate("FD.k = 0"); p.wait_for_function('!FD.busy', timeout=3000)
    for i in range(11): p.click('#fJar'); p.wait_for_timeout(40)
    check('the plate holds ten; one more and the jar shakes', p.evaluate('FD.k') == 10 and 'nope' in p.get_attribute('#fJar', 'class'))
    p.evaluate("FD.k = 0; drawPlate()")
    for k in range(1, 5):
        p.wait_for_function(f'FD.n === {k} && !FD.busy', timeout=6000)
        for i in range(p.evaluate('FD.want')): p.click('#fJar'); p.wait_for_timeout(30)
        p.click('#fFeed')
    p.wait_for_function("!document.getElementById('fEnd').hidden", timeout=10000)
    check(f'end of the round: "{p.text_content("#fEndWord")}", 4 green dots and 1 pink', p.text_content('#fEndWord') == 'Happy monsters!'
          and p.eval_on_selector_all('#fEndDots i.hit', 'e => e.length') == 4 and p.eval_on_selector_all('#fEndDots i.miss', 'e => e.length') == 1 and p.is_hidden('#fPlate'))
    p.screenshot(path=OUT / 'f3_feed_end.png')
    p.click('#fAgain'); p.wait_for_timeout(300)
    check('Play again starts a new round', p.is_hidden('#fEnd') and p.is_visible('#fPlate') and p.evaluate('FD.n') == 0)
    p.click('#fLevels .level >> nth=1'); p.wait_for_timeout(300)
    q = p.evaluate('FD.queue.map(x => x.want)')
    check(f'Medium: amounts from 3 to 10 ({q})', all(3 <= v <= 10 for v in q) and len(set(q)) == 5)
    p.click('#fLevels .level >> nth=2'); p.wait_for_timeout(500)
    q = p.evaluate('FD.queue')
    check(f'Tricky: one more or one less, both kinds, from a plate of 2 to 9 ({[(x["start"], x["dir"]) for x in q]})',
          len(q) == 5 and all(2 <= x['start'] <= 9 and x['want'] == x['start'] + x['dir'] and x['dir'] in (1, -1) for x in q) and {x['dir'] for x in q} == {1, -1})
    for k in range(5):
        p.wait_for_function(f'FD.n === {k} && !FD.busy && FD.k === FD.start', timeout=6000)
        st, d = p.evaluate('FD.start'), p.evaluate('FD.dir')
        if k == 0:
            p.wait_for_function("window.__said.length > 0", timeout=3000); p.wait_for_timeout(700)
            check(f'Tricky: the plate starts with {st}, the bubble says {p.text_content("#fNum")}, "{said(p)[-1]}"',
                  p.eval_on_selector_all('#fPlate .ck', 'e => e.length') == st and p.text_content('#fNum') == ('+1' if d > 0 else '−1')
                  and said(p)[-1] == page_lines['f_one_more' if d > 0 else 'f_one_less'])
            p.screenshot(path=OUT / 'f4_feed_tricky.png')
        if d > 0:
            p.click('#fJar'); p.wait_for_timeout(150)
            if k == 0: check(f'  one more: counting on from {st} ("{said(p)[-1]}")', said(p)[-1] == LINES_N[st + 1])
        else:
            p.click(f'#fPlate .fslot >> nth={st - 1}'); p.wait_for_timeout(150)
        p.click('#fFeed')
    p.wait_for_function("!document.getElementById('fEnd').hidden", timeout=10000)
    check(f'Tricky round done: "{p.text_content("#fEndWord")}"', p.text_content('#fEndWord') == 'All first go!')
    p.click('#feedgame .back'); p.wait_for_timeout(300)
    p.evaluate("location.hash = '#feed'"); p.wait_for_timeout(400)
    check('it remembers the level (Tricky)', p.get_attribute('#fLevels .level >> nth=2', 'aria-pressed') == 'true')
    ctx.close()

    # ---------------------------------------------------------------- More or less, phone
    ctx, p = page_at(b, 390, 844)
    p.goto(BASE); p.wait_for_timeout(400)
    p.click('#playMore'); p.wait_for_function('MR.a > 0', timeout=5000)
    check('More or less opens #more with 3 levels and 6 dots', p.evaluate('location.hash') == '#more' and p.eval_on_selector_all('#mLevels .level', 'e => e.length') == 3
          and p.eval_on_selector_all('#mProg i', 'e => e.length') == 6)
    q = p.evaluate('MR.queue')
    pairs = sorted(tuple(sorted((x['a'], x['b']))) for x in q)
    check(f'Easy: six different pairs from 1 to 5, at least 2 apart, always "more" ({pairs})', len(set(pairs)) == 6 and all(1 <= a and b <= 5 and b - a >= 2 for a, b in pairs) and all(x['ask'] == 'more' for x in q))
    p.wait_for_function("window.__said.length > 0", timeout=4000)
    check(f'"Which side has more?", said and on screen', said(p)[0] == page_lines['m_more'] and p.text_content('#mQText') == page_lines['m_more'])
    a, bb = p.evaluate('MR.a'), p.evaluate('MR.b')
    nl, nr = p.eval_on_selector_all('#mL .mmon', 'e => e.length'), p.eval_on_selector_all('#mR .mmon', 'e => e.length')
    sizes = p.evaluate("[$('mL'), $('mR')].map(s => s.style.getPropertyValue('--m'))")
    check(f'{a} monsters on the left, {bb} on the right, all the same size on Easy ({sizes})', (nl, nr) == (a, bb) and sizes[0] == sizes[1])
    srcs = p.evaluate("[...['mL', 'mR']].map(id => [...new Set([...$(id).querySelectorAll('img')].map(i => i.src))])")
    check('one kind of monster on each side, a different one on each', len(srcs[0]) == 1 and len(srcs[1]) == 1 and srcs[0] != srcs[1])
    for side in ('mL', 'mR'):
        o = overlap_report(p, f'#{side} .mmon', f'#{side}')
        check(f'  {side}: none overlapping, all inside, each {o["min"]} px', o['over'] == 0 and o['out'] == 0)
    p.screenshot(path=OUT / 'm1_more.png')
    p.evaluate("MR.queue[0] = { a: 2, b: 5, ask: 'more' }; MR.n = 0; moreNext()"); p.wait_for_timeout(600)
    n0 = len(said(p))
    p.click('#mL'); p.wait_for_timeout(200)
    check('the wrong side shakes, "Let\'s count them."', 'nope' in p.get_attribute('#mL', 'class') and page_lines['m_count'] in said(p)[n0:])
    p.wait_for_function("!MR.busy", timeout=10000)
    after = said(p)[n0:]
    check(f'it counts one side, then the other ({after[1:]}), and asks again', after[1:8] == ['one', 'two', 'one', 'two', 'three', 'four', 'five'] and after[-1] == page_lines['m_more']
          and p.eval_on_selector_all('.mside .mmon.done', 'e => e.length') == 7 and 'shown' in p.get_attribute('#mL', 'class') and 'shown' in p.get_attribute('#mR', 'class'))
    check('  every monster wears its number, and each side its total', p.eval_on_selector_all('#mR .mmon b', 'e => e.map(x => x.textContent)') == ['1', '2', '3', '4', '5']
          and p.text_content('#mL .mtot') == '2' and p.text_content('#mR .mtot') == '5')
    p.screenshot(path=OUT / 'm2_more_counted.png')
    p.click('#mR'); p.wait_for_timeout(200)
    check('the right side: it bounces and goes green', 'yes' in p.get_attribute('#mR', 'class'))
    p.wait_for_function('MR.n === 1', timeout=6000)
    check('  praise, a pink dot (it took two goes), then the next pair', p.eval_on_selector_all('#mProg i.miss', 'e => e.length') == 1 and not p.evaluate("$('mL').classList.contains('shown')"))
    for k in range(1, 6):
        p.wait_for_function(f'MR.n === {k} && !MR.busy', timeout=6000)
        p.click('#mL' if p.evaluate('MR.a > MR.b') else '#mR')
    p.wait_for_function("!document.getElementById('mEnd').hidden", timeout=10000)
    check(f'end of the round: "{p.text_content("#mEndWord")}", 5 green dots and 1 pink', p.text_content('#mEndWord') == 'Well done!'
          and p.eval_on_selector_all('#mEndDots i.hit', 'e => e.length') == 5 and p.eval_on_selector_all('#mEndDots i.miss', 'e => e.length') == 1 and p.is_hidden('#mCmp'))
    p.click('#mLevels .level >> nth=1'); p.wait_for_timeout(500)
    q = p.evaluate('MR.queue')
    check(f'Medium: pairs from 2 to 10, at least 2 apart ({[(x["a"], x["b"]) for x in q]})', all(2 <= min(x['a'], x['b']) and max(x['a'], x['b']) <= 10 and abs(x['a'] - x['b']) >= 2 for x in q))
    bigger = []
    for k in range(6):
        p.wait_for_function(f'MR.n === {k} && !MR.busy', timeout=6000)
        m = p.evaluate("[$('mL'), $('mR')].map(s => parseFloat(s.style.getPropertyValue('--m')))")
        few = 0 if p.evaluate('MR.a < MR.b') else 1
        bigger.append(m[few] >= m[1 - few])
        if k == 0: p.screenshot(path=OUT / 'm3_more_medium.png')
        p.click('#mL' if p.evaluate('MR.a > MR.b') else '#mR')
    check(f'Medium: the side with fewer has the bigger monsters, every time ({bigger})', all(bigger))
    p.click('#mLevels .level >> nth=2'); p.wait_for_timeout(500)
    q = p.evaluate('MR.queue')
    check(f'Tricky: only 1 or 2 apart, 3 to 10, three "more" and three "fewer" ({[(x["a"], x["b"], x["ask"]) for x in q]})',
          all(3 <= min(x['a'], x['b']) and max(x['a'], x['b']) <= 10 and 1 <= abs(x['a'] - x['b']) <= 2 for x in q) and sorted(x['ask'] for x in q) == ['fewer'] * 3 + ['more'] * 3)
    for k in range(6):
        p.wait_for_function(f'MR.n === {k} && !MR.busy', timeout=6000)
        ask = p.evaluate('MR.ask')
        if ask == 'fewer' and 'fewer_seen' not in locals():
            fewer_seen = True
            p.wait_for_timeout(500)
            check(f'"Which side has fewer?" on screen and said', p.text_content('#mQText') == page_lines['m_fewer'] and said(p)[-1] == page_lines['m_fewer'])
        left = p.evaluate('MR.a > MR.b') == (ask == 'more')
        p.click('#mL' if left else '#mR')
    p.wait_for_function("!document.getElementById('mEnd').hidden", timeout=10000)
    check(f'Tricky round done, picking fewer when asked: "{p.text_content("#mEndWord")}"', p.text_content('#mEndWord') == 'All first go!')
    ctx.close()

    # every pair at every size: monsters inside their side, never overlapping, big enough to count
    for (w, h, name) in ((360, 740, 'small phone'), (390, 844, 'phone'), (904, 1000, 'folding phone open'), (1280, 800, 'laptop')):
        ctx, p = page_at(b, w, h, touch=w < 1000)
        p.goto(BASE + '#more'); p.wait_for_function("document.querySelectorAll('#mL .mmon').length > 0", timeout=5000)
        r = p.evaluate("""(() => { const out = [];
          for (const lv of ['1', '2']) for (let n = 1; n <= 10; n++) { MR.level = lv; MR.a = n; MR.b = n === 10 ? 9 : 10; let small = 1e9, bad = 0;
            for (let t = 0; t < 20; t++) { placeMore();
              for (const id of ['mL', 'mR']) { const s = $(id).getBoundingClientRect(), r = [...$(id).querySelectorAll('.mmon')].map(e => e.getBoundingClientRect());
                r.forEach((a, i) => { small = Math.min(small, a.width);
                  if (a.left < s.left - 1 || a.right > s.right + 1 || a.top < s.top - 1 || a.bottom > s.bottom + 1) bad++;
                  r.slice(i + 1).forEach(c => { if (Math.hypot(a.left - c.left, a.top - c.top) < Math.min(a.width, c.width) * .92) bad++; }); }); } }
            out.push({ lv, n, small: Math.round(small), bad }); }
          return out; })()""")
        bad = [x for x in r if x['bad']]
        smallest = min(x['small'] for x in r)
        check(f'{name} {w}px: every amount up to 10, x 20 layouts on each side, none overlapping or outside; smallest {smallest} px{": " + str(bad[:3]) if bad else ""}',
              not bad and smallest >= 30)
        p.goto(BASE + '#feed'); p.wait_for_function('FD.want > 0', timeout=5000); p.wait_for_timeout(300)
        g = p.evaluate("""(() => { const s = parseFloat($('fPlate').style.getPropertyValue('--s')), row = $('fRow').getBoundingClientRect(), jar = $('fJar').getBoundingClientRect();
          return { s, bottom: Math.round(row.bottom + scrollY), jar: Math.round(jar.width), feed: Math.round($('fFeed').getBoundingClientRect().height) }; })()""")
        check(f'{name}: cookie spaces {g["s"]:.0f} px, the jar {g["jar"]} px and Feed {g["feed"]} px tall, all on the first screen (bottom {g["bottom"]} of {h})',
              g['s'] >= 38 and g['jar'] >= 76 and g['feed'] >= 60 and g['bottom'] <= h)
        if w == 360: p.screenshot(path=OUT / 'f5_feed_small.png')
        ctx.close()

    # ---------------------------------------------------------------- Monster train, phone
    ctx, p = page_at(b, 390, 844)
    p.goto(BASE); p.wait_for_timeout(400)
    p.click('#playTrain'); p.wait_for_function('TR.want > 0', timeout=5000)
    check('Monster train opens #train with 3 levels and 6 dots', p.evaluate('location.hash') == '#train' and p.eval_on_selector_all('#trLevels .level', 'e => e.length') == 3
          and p.eval_on_selector_all('#trProg i', 'e => e.length') == 6)
    q = p.evaluate('TR.queue')
    check(f'Easy: six trains counting up from 1 to 6, the last carriage empty ({[x["seq"] for x in q]})',
          sorted(x['seq'][0] for x in q) == [1, 2, 3, 4, 5, 6] and all(x['seq'] == list(range(x['seq'][0], x['seq'][0] + 4)) and x['gap'] == 3 and x['kind'] == 'next' for x in q))
    p.evaluate("TR.queue[0] = { seq: [3, 4, 5, 6], gap: 3, kind: 'next' }; TR.n = 0; trainNext()")
    p.wait_for_function('!TR.busy', timeout=5000)
    nums = p.eval_on_selector_all('#trTrain .car b', 'e => e.map(x => x.textContent)')
    check(f'it pulls in: four carriages and an engine, the last one empty ({nums})', nums == ['3', '4', '5', '?'] and p.eval_on_selector_all('#trTrain .eng', 'e => e.length') == 1
          and 'gap' in p.get_attribute('#trTrain .car >> nth=3', 'class'))
    p.wait_for_function(f"window.__said.includes({json.dumps(page_lines['t_next'])})", timeout=6000)
    check(f'the narrator reads along, then asks ({said(p)[-4:]})', said(p)[-4:] == ['three', 'four', 'five', page_lines['t_next']])
    tiles = p.eval_on_selector_all('#trTiles .ntile', 'e => e.map(x => +x.dataset.n)')
    check(f'three numbers to pick from, in order ({tiles})', 6 in tiles and len(tiles) == 3 and tiles == sorted(tiles))
    p.screenshot(path=OUT / 't1_train.png')
    wrong = next(v for v in tiles if v != 6); n0 = len(said(p))
    p.click(tile(p, 'trTiles', wrong)); p.wait_for_timeout(150)
    check('a wrong number shakes, "Let\'s count along."', 'nope' in p.get_attribute(tile(p, 'trTiles', wrong), 'class') and p.evaluate('TR.busy'))
    p.wait_for_function('!TR.busy', timeout=10000)
    check(f'  it counts up to the empty carriage, then asks again ({said(p)[n0:]})', said(p)[n0:] == [page_lines['t_count'], 'three', 'four', 'five', page_lines['t_next']])
    p.click(tile(p, 'trTiles', 6)); p.wait_for_timeout(250)
    check('the right number: a monster hops into the empty carriage, which gets its number', 'fill' in p.get_attribute('#trTrain .car >> nth=3', 'class')
          and p.text_content('#trTrain .car >> nth=3') == '6')
    p.wait_for_function("document.getElementById('trTrain').classList.contains('go')", timeout=5000)
    check('  "six", praise, and off the train goes', 'six' in said(p)[n0:])
    p.wait_for_function('TR.n === 1 && !TR.busy', timeout=8000)
    check('  then the next train, and a pink dot (it took two goes)', p.eval_on_selector_all('#trProg i.miss', 'e => e.length') == 1 and p.text_content('#trTrain .car >> nth=3') == '?')
    for k in range(1, 6):
        p.wait_for_function(f'TR.n === {k} && !TR.busy', timeout=8000)
        p.click(tile(p, 'trTiles', p.evaluate('TR.want')))
    p.wait_for_function("!document.getElementById('trEnd').hidden", timeout=12000)
    check(f'end of the round: "{p.text_content("#trEndWord")}", 5 green dots and 1 pink', p.text_content('#trEndWord') == 'Toot toot!'
          and p.eval_on_selector_all('#trEndDots i.hit', 'e => e.length') == 5 and p.eval_on_selector_all('#trEndDots i.miss', 'e => e.length') == 1 and p.is_hidden('#trScene'))
    p.click('#trLevels .level >> nth=1'); p.wait_for_timeout(300)
    q = p.evaluate('TR.queue')
    check(f'Medium: up to 10, four with a carriage missing in the middle and two at the end ({[(x["seq"], x["gap"]) for x in q]})',
          all(x['seq'][3] <= 10 for x in q) and sorted(x['gap'] for x in q) == [1, 1, 2, 2, 3, 3] and all((x['kind'] == 'missing') == (x['gap'] < 3) for x in q))
    p.evaluate("TR.queue[0] = { seq: [5, 6, 7, 8], gap: 1, kind: 'missing' }; TR.n = 0; trainNext()")
    p.wait_for_function(f"window.__said.slice(-1)[0] === {json.dumps(page_lines['t_missing'])}", timeout=8000)
    check(f'missing in the middle: it reads round the gap and asks "{said(p)[-1]}"', said(p)[-4:] == ['five', 'seven', 'eight', page_lines['t_missing']])
    p.click('#trLevels .level >> nth=2'); p.wait_for_timeout(300)
    q = p.evaluate('TR.queue')
    check(f'Tricky: up to 20, three "what comes before" and three counting down ({[(x["seq"], x["kind"]) for x in q]})',
          sorted(x['kind'] for x in q) == ['before'] * 3 + ['down'] * 3 and all(max(x['seq']) <= 20 and min(x['seq']) >= 1 for x in q)
          and all(x['gap'] == 0 and x['seq'] == sorted(x['seq']) for x in q if x['kind'] == 'before') and all(x['gap'] == 3 and x['seq'] == sorted(x['seq'], reverse=True) for x in q if x['kind'] == 'down'))
    p.evaluate("TR.queue[0] = { seq: [14, 13, 12, 11], gap: 3, kind: 'down' }; TR.n = 0; trainNext()")
    p.wait_for_function(f"window.__said.slice(-1)[0] === {json.dumps(page_lines['t_next'])}", timeout=8000)
    check(f'counting down: "Counting down!", the numbers, "What comes next?", and 4 numbers to pick from',
          said(p)[-5:] == [page_lines['t_down'], 'fourteen', 'thirteen', 'twelve', page_lines['t_next']] and p.eval_on_selector_all('#trTiles .ntile', 'e => e.length') == 4)
    p.wait_for_function('!TR.busy', timeout=3000)
    p.evaluate("TR.queue[0] = { seq: [9, 10, 11, 12], gap: 0, kind: 'before' }; TR.n = 0; trainNext()")
    p.wait_for_function(f"window.__said.slice(-1)[0] === {json.dumps(page_lines['t_before'])}", timeout=8000)
    check(f'what comes before: the front carriage is empty, "{said(p)[-1]}"', p.text_content('#trTrain .car >> nth=0') == '?' and said(p)[-4:] == ['ten', 'eleven', 'twelve', page_lines['t_before']])
    p.screenshot(path=OUT / 't2_train_before.png')
    tiles = p.eval_on_selector_all('#trTiles .ntile', 'e => e.map(x => +x.dataset.n)'); n0 = len(said(p))
    p.click(tile(p, 'trTiles', next(v for v in tiles if v != 9))); p.wait_for_function('!TR.busy', timeout=10000)
    check(f'  a wrong answer there counts backwards to the gap ({said(p)[n0:]})', said(p)[n0:] == [page_lines['t_count'], 'twelve', 'eleven', 'ten', page_lines['t_before']])
    p.click('#traingame .back'); p.wait_for_timeout(300)
    p.evaluate("location.hash = '#train'"); p.wait_for_timeout(400)
    check('it remembers the level (Tricky)', p.get_attribute('#trLevels .level >> nth=2', 'aria-pressed') == 'true')
    ctx.close()

    # ---------------------------------------------------------------- Jump in the bed, phone
    ctx, p = page_at(b, 390, 844)
    p.goto(BASE); p.wait_for_timeout(400)
    p.click('#playJump'); p.wait_for_function('JB.a > 0', timeout=5000)
    check('Jump in the bed opens #jump with 3 levels and 6 dots', p.evaluate('location.hash') == '#jump' and p.eval_on_selector_all('#jLevels .level', 'e => e.length') == 3
          and p.eval_on_selector_all('#jProg i', 'e => e.length') == 6)
    q = p.evaluate('JB.queue')
    check(f'Easy: six different sums up to 5, one or two jumping on ({[(x["a"], x["b"]) for x in q]})',
          len({(x['a'], x['b']) for x in q}) == 6 and all(x['kind'] == 'on' and x['a'] >= 1 and 1 <= x['b'] <= 2 and x['a'] + x['b'] <= 5 for x in q))
    p.evaluate("JB.queue[0] = { a: 3, b: 2, kind: 'on' }; JB.n = 0; jumpNext()"); p.wait_for_timeout(200)
    check('the story starts with three on the bed, the other two waiting off to the side', p.eval_on_selector_all('#jMons .jmon', 'e => e.length') == 5
          and p.eval_on_selector_all('#jMons .jmon.away', 'e => e.length') == 2 and p.is_hidden('#jTiles'))
    p.wait_for_function('!JB.busy', timeout=8000)
    said_now = said(p)
    check(f'"Three monsters on the bed." "Two more jump on!" "How many on the bed now?"', said_now[-3:] == [page_lines['j_bed_3'], page_lines['j_on_2'], page_lines['j_how_many']])
    srcs = p.eval_on_selector_all('#jMons .jmon img', 'e => e.map(x => x.src)')
    check('they jumped on, and they\'re a different monster from the three already there', p.eval_on_selector_all('#jMons .jmon.away', 'e => e.length') == 0
          and len(set(srcs[:3])) == 1 and len(set(srcs[3:])) == 1 and srcs[0] != srcs[3])
    tiles = p.eval_on_selector_all('#jTiles .ntile', 'e => e.map(x => +x.dataset.n)')
    check(f'three numbers to pick from ({tiles}), and Watch again', 5 in tiles and len(tiles) == 3 and p.is_visible('#jWatch'))
    p.screenshot(path=OUT / 'j1_jump.png')
    n0 = len(said(p)); p.click('#jWatch'); p.wait_for_timeout(150)
    check('Watch again: back to three on the bed, the two off to the side again', p.evaluate('JB.busy') and p.eval_on_selector_all('#jMons .jmon.away', 'e => e.length') == 2 and p.is_hidden('#jTiles'))
    p.wait_for_function('!JB.busy', timeout=8000)
    check('  and it tells the story again, with the same numbers to pick from', said(p)[n0:] == [page_lines['j_bed_3'], page_lines['j_on_2'], page_lines['j_how_many']]
          and p.eval_on_selector_all('#jTiles .ntile', 'e => e.map(x => +x.dataset.n)') == tiles)
    wrong = next(v for v in tiles if v != 5); n0 = len(said(p))
    p.click(tile(p, 'jTiles', wrong)); p.wait_for_timeout(150)
    check('a wrong number shakes', 'nope' in p.get_attribute(tile(p, 'jTiles', wrong), 'class'))
    p.wait_for_function('!JB.busy', timeout=10000)
    check(f'  "Let\'s count them.", a number on each monster on the bed, and the question again ({said(p)[n0:]})',
          said(p)[n0:] == [page_lines['m_count'], 'one', 'two', 'three', 'four', 'five', page_lines['j_how_many']] and p.eval_on_selector_all('#jMons .jmon.done', 'e => e.length') == 5)
    p.screenshot(path=OUT / 'j2_jump_counted.png')
    p.click(tile(p, 'jTiles', 5)); p.wait_for_timeout(200)
    check('the right number: they all bounce', 'happy' in p.get_attribute('#jScene', 'class') and 'yes' in p.get_attribute(tile(p, 'jTiles', 5), 'class'))
    p.wait_for_function('JB.n === 1', timeout=6000)
    check('  then the next story, and a pink dot', p.eval_on_selector_all('#jProg i.miss', 'e => e.length') == 1)
    for k in range(1, 6):
        p.wait_for_function(f'JB.n === {k} && !JB.busy && !document.getElementById("jTiles").hidden', timeout=10000)
        p.click(tile(p, 'jTiles', p.evaluate('JB.total')))
    p.wait_for_function("!document.getElementById('jEnd').hidden", timeout=12000)
    check(f'end of the round: "{p.text_content("#jEndWord")}", 5 green dots and 1 pink', p.text_content('#jEndWord') == 'Great counting!'
          and p.eval_on_selector_all('#jEndDots i.hit', 'e => e.length') == 5 and p.is_hidden('#jScene') and p.is_hidden('#jWatch'))
    p.click('#jLevels .level >> nth=1'); p.wait_for_timeout(300)
    q = p.evaluate('JB.queue')
    check(f'Medium: sums from 5 to 10, up to three jumping on ({[(x["a"], x["b"]) for x in q]})', all(x['kind'] == 'on' and 5 <= x['a'] + x['b'] <= 10 and 1 <= x['b'] <= 3 for x in q))
    p.click('#jLevels .level >> nth=2'); p.wait_for_timeout(300)
    q = p.evaluate('JB.queue')
    check(f'Tricky: three jump on and three roll off, never below one ({[(x["a"], x["b"], x["kind"]) for x in q]})',
          sorted(x['kind'] for x in q) == ['off'] * 3 + ['on'] * 3 and all(x['a'] - x['b'] >= 1 for x in q if x['kind'] == 'off') and all(x['a'] + x['b'] <= 10 for x in q if x['kind'] == 'on'))
    p.evaluate("JB.queue[0] = { a: 8, b: 2, kind: 'off' }; JB.n = 0; jumpNext()")
    p.wait_for_function('!JB.busy', timeout=8000)
    check(f'rolling off: "Eight monsters on the bed." "Oops! Two roll off!" and six left, with 4 numbers to pick from',
          said(p)[-3:] == [page_lines['j_bed_8'], page_lines['j_off_2'], page_lines['j_how_many']] and p.eval_on_selector_all('#jMons .jmon:not(.off)', 'e => e.length') == 6
          and p.eval_on_selector_all('#jMons .jmon.off', 'e => e.length') == 2 and p.eval_on_selector_all('#jTiles .ntile', 'e => e.length') == 4)
    p.wait_for_timeout(700); p.screenshot(path=OUT / 'j3_jump_off.png')
    ctx.close()

    # every amount at every size: the train fits, the bed holds ten
    for (w, h, name) in ((360, 740, 'small phone'), (390, 844, 'phone'), (904, 1000, 'folding phone open'), (1280, 800, 'laptop')):
        ctx, p = page_at(b, w, h, touch=w < 1000)
        p.goto(BASE + '#train'); p.wait_for_function('!TR.busy && TR.want > 0', timeout=6000)
        p.evaluate("TR.queue[0] = { seq: [20, 19, 18, 17], gap: 3, kind: 'down' }; TR.n = 0; trainNext()"); p.wait_for_function('!TR.busy', timeout=6000)
        g = p.evaluate("""(() => { const sc = $('trScene').getBoundingClientRect(), r = [...document.querySelectorAll('#trTrain .car, #trTrain .eng')].map(e => e.getBoundingClientRect());
          const nums = [...document.querySelectorAll('#trTrain .car b')].map(e => ({ w: e.scrollWidth, cw: e.clientWidth }));
          return { inside: r.every(x => x.left >= sc.left - 1 && x.right <= sc.right + 1 && x.top >= sc.top - 1), c: parseFloat($('trScene').style.getPropertyValue('--c')),
                   font: parseFloat(getComputedStyle(document.querySelector('#trTrain .car b')).fontSize), fits: nums.every(n => n.w <= n.cw + 1) }; })()""")
        check(f'{name} {w}px: the whole train is on screen, carriages {g["c"]:.0f} px, numbers {g["font"]:.0f} px and two-digit ones fit', g['inside'] and g['c'] >= 40 and g['font'] >= 16 and g['fits'])
        p.goto(BASE + '#jump'); p.wait_for_function('JB.a > 0', timeout=5000)
        r = p.evaluate("""(() => { JB.a = 10; JB.b = 0; JB.kind = 'on'; placeJump();
          const sc = $('jScene').getBoundingClientRect(), all = [...document.querySelectorAll('#jMons .jmon')], r = all.map(e => e.getBoundingClientRect());
          const front = r.filter((x, i) => all[i].style.zIndex === '3'), back = r.filter((x, i) => all[i].style.zIndex === '1');
          let over = 0; [front, back].forEach(row => row.forEach((a, i) => row.slice(i + 1).forEach(c => { if (Math.abs(a.left - c.left) < a.width * .98) over++; })));
          const shown = back.map(x => Math.max(0, Math.min(1, (Math.min(...front.map(f => f.top)) - x.top) / x.height)));
          return { n: r.length, over, inside: r.every(x => x.left >= sc.left - 1 && x.right <= sc.right + 1 && x.top >= sc.top - 1), m: Math.round(r[0].width), shown: Math.min(...shown) }; })()""")
        check(f'{name}: ten on the bed, {r["m"]} px each, no two in a row overlapping, all in the picture, the back row at least {r["shown"]:.0%} showing',
              r['n'] == 10 and r['over'] == 0 and r['inside'] and r['m'] >= 36 and r['shown'] >= .6)
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
        broken = [i for i in idx['clips'] if not (real / f'{i}.mp3').exists()]
        check(f'the real narrator: {len(idx["clips"])} clips, every one listed is there{": " + str(broken) if broken else ""}', not broken)
        # new lines get their clips when the voice maker is run again; until then the browser's voice says them
        print(f'note: {len(missing)} lines have no clip yet: {", ".join(missing)}' if missing else 'ok   every line has a clip')
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
        for hsh in ('#count', '#quick', '#feed', '#more', '#train', '#jump', ''):
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
        with tempfile.TemporaryDirectory() as td:       # Google's daily allowance runs out part way through
            td = Path(td)
            for f in ('number_voices.py', 'number_lines.json'): (td / f).write_bytes((NUMBERS / f).read_bytes())
            m = subprocess.Popen([sys.executable, str(mock), '8797', 'daily']); time.sleep(.8)
            env = {**os.environ, 'GEN_API_BASE': 'http://127.0.0.1:8797/v1beta', 'GEMINI_API_KEY': 'test-key', 'GEN_PACE': '0'}
            try:
                t0 = time.time()
                r = subprocess.run([sys.executable, 'number_voices.py'], cwd=td, env=env, capture_output=True, text=True, timeout=60)
                made = len(list((td / 'voices' / 'narrator').glob('*.wav')))
                check(f'daily limit: it keeps the {made} it made, stops straight away ({time.time() - t0:.1f} s) and says when to try again',
                      made == 2 and time.time() - t0 < 15 and 'daily limit' in r.stdout and 'run this again after about' in r.stdout and '100 a day' in r.stdout
                      and (td / 'listen.html').exists())
            finally:
                m.kill()

print('PROBLEMS:' if problems else 'no problems')
for x in problems: print('  ', x)
sys.exit(1 if problems else 0)
