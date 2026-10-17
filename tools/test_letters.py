"""Play Letters: trace every letter the way a finger would, check the wrong start, wrong way and off-the-line nudges,
and spell words at every level. Phone, folding-phone and laptop sizes.
    python3 tools/test_letters.py OUTDIR"""
import http.server, socketserver, sys, threading, functools, json, subprocess, tempfile, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent          # the repo root, where index.html lives
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
socketserver.TCPServer.allow_reuse_address = True
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
PORT = 8831
srv = socketserver.TCPServer(('127.0.0.1', PORT), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{PORT}/index.html'
css = ("@font-face{font-family:'Fredoka';font-weight:300 700;src:url(http://127.0.0.1:%d/Fredoka.ttf)}"
       "@font-face{font-family:'Nunito';font-weight:200 1000;src:url(http://127.0.0.1:%d/Nunito.ttf)}") % (PORT, PORT)
problems = []
FAM_FILE = SITE / 'letters' / 'family.json'                # private: on the family's copy only, not in the repo
FAM_IDS = set(json.loads(FAM_FILE.read_text())['words']) if FAM_FILE.exists() else set()
KID = 'Sam'   # the name used for the family browser here (family words follow the pass, never a name)
def check(label, ok):
    print(('ok   ' if ok else 'FAIL ') + label)
    if not ok: problems.append(label)

# a stand-in voice: a short tone for a few clips, so the recorded-voice path is exercised too
TMP = Path(tempfile.mkdtemp())
subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.25', '-ac', '1', '-b:a', '48k', str(TMP / 'tone.mp3')], check=True)
TONE = (TMP / 'tone.mp3').read_bytes()
FAKE_VOICE = {'mum': ['say_watch', 'say_trace', 'sound_a', 'word_axolotl', 'say_spell', 'sound_f', 'sound_o', 'sound_x', 'word_fox'], 'dad': []}

def page_at(b, w, h, touch=True, voices=False, passed=True):
    ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=touch, has_touch=touch)
    if passed:   # this device has opened the secret link (the hosted build hides Letters otherwise)
        ctx.add_cookies([{'name': 'mb_letters_ok', 'value': '1', 'url': f'http://127.0.0.1:{PORT}'}])
    ctx.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=css))
    ctx.route('https://fonts.gstatic.com/**', lambda r: r.abort())
    if voices is True:          # the stand-in tone
        ctx.route('**/letters/voices/index.json', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(FAKE_VOICE)))
        ctx.route('**/letters/voices/mum/*.mp3', lambda r: r.fulfill(status=200, content_type='audio/mpeg', body=TONE))
    elif voices is False:       # as if nothing had been recorded
        ctx.route('**/letters/voices/index.json', lambda r: r.fulfill(status=200, content_type='application/json', body='{"mum":[],"dad":[]}'))
    # voices == 'real': the recorded clips in site/letters/voices
    p = ctx.new_page()
    # a copy with no family file gets one 404 for it, and that's expected
    p.on('console', lambda m: m.type == 'error' and 'family.json' not in (m.location or {}).get('url', '') and problems.append(f'console error: {m.text}'))
    p.on('pageerror', lambda e: problems.append(f'page error: {e}'))
    return ctx, p

def skip_demo(p):
    p.wait_for_function('typeof LT !== "undefined" && LT.strokes.length > 0')
    p.evaluate('LT.demoTok++; LT.demoing = false; voice.stop(); LT.strokes.forEach(s => { if (s.ghost) s.ghost.setAttribute("stroke-dasharray", `0 ${s.L + 400}`); else s.g.classList.remove("done"); }); lmarks();')

def screen_pts(p, k, step=14, upto=None, frm=0):
    """Points of stroke k in page pixels, every `step` font units (the path a finger would take)."""
    return p.evaluate("""([k, step, upto, frm]) => { const s = LT.strokes[k], svg = $('tSvg'), m = svg.getScreenCTM(), out = [];
        if (s.dot) { const q = new DOMPoint(s.dot[0], -s.dot[1]).matrixTransform(m); return [[q.x, q.y]]; }
        const end = upto == null ? s.L : upto;
        for (let a = frm; a <= end; a += step) { const [x, y] = lat(s, a); const q = new DOMPoint(x, -y).matrixTransform(m); out.push([q.x, q.y]); }
        const [x, y] = lat(s, end); const q = new DOMPoint(x, -y).matrixTransform(m); out.push([q.x, q.y]); return out; }""", [k, step, upto, frm])

def trace_stroke(p, k, **kw):
    pts = screen_pts(p, k, **kw)
    p.mouse.move(*pts[0]); p.mouse.down()
    for pt in pts[1:]: p.mouse.move(*pt)
    p.mouse.up()

def trace_letter(p, ch):
    p.evaluate(f'setLetter("{ch}")'); skip_demo(p)
    n = p.evaluate('LT.strokes.length')
    for k in range(n): trace_stroke(p, k)
    return p.evaluate('LT.done')

with sync_playwright() as pw:
    b = pw.chromium.launch()
    # ---------------------------------------------------------------- phone, a family browser (it has the pass)
    ctx, p = page_at(b, 390, 844, voices=True)
    p.goto(BASE + f'?for={KID}'); p.wait_for_timeout(700)
    check('the Learning Lab opens on its games: 7, Letters among them', p.eval_on_selector_all('.gametile', 'e => e.length') == 7 and p.is_visible('#playLetters') and p.is_visible('#home'))
    p.click('#playLetters'); p.wait_for_timeout(400)
    check('Letters tile opens #letters on Trace', p.evaluate('location.hash') == '#letters' and p.is_visible('#traceBox') and not p.is_visible('#spellBox'))
    check('it starts by showing how ("Watch me first.")', p.evaluate('LT.demoing') and 'Watch me first' in p.text_content('#lSay'))
    p.screenshot(path=OUT / 'l1_demo.png')
    # tapping during the demo does nothing
    pts = screen_pts(p, 0)
    p.mouse.click(*pts[0]);
    check('taps during the demo are ignored', p.evaluate('LT.prog') == 0 and not p.evaluate('LT.down'))
    p.wait_for_function('!LT.demoing', timeout=15000); p.wait_for_timeout(200)
    check('then "Your turn" and a green start dot', 'Your turn' in p.text_content('#lSay') and p.eval_on_selector_all('#tSvg .start', 'e => e.length') == 1)
    check('the recorded voice is used when there is one (Mum)', p.evaluate('voice.who') == 'mum' and p.evaluate('voice.has("sound_a")'))
    p.screenshot(path=OUT / 'l2_your_turn.png')
    # wrong start: touching the bottom of the a's stem
    end = screen_pts(p, 0)[-1]
    p.mouse.move(*end); p.mouse.down(); p.mouse.move(end[0], end[1] - 30); p.mouse.up(); p.wait_for_timeout(100)
    check('starting at the wrong end does nothing and says "Start at the green dot."', p.evaluate('LT.prog') == 0 and 'green dot' in p.text_content('#lSay'))
    p.wait_for_timeout(2600)
    # wrong way: go forward a bit, then back
    part = screen_pts(p, 0, upto=300)
    p.mouse.move(*part[0]); p.mouse.down()
    for pt in part[1:]: p.mouse.move(*pt)
    prog = p.evaluate('LT.prog')
    for pt in reversed(part[:-1]): p.mouse.move(*pt)
    check(f'going backwards doesn\'t undo or fill ({prog:.0f} units kept) and says "Follow the arrow."', abs(p.evaluate('LT.prog') - prog) < 1 and 'arrow' in p.text_content('#lSay'))
    p.mouse.up(); p.wait_for_timeout(2600)
    # off the line: carry on, then wander far off
    start_prog = p.evaluate('LT.prog')
    part = screen_pts(p, 0, upto=500, frm=start_prog)
    p.mouse.move(*screen_pts(p, 0, upto=start_prog)[-1]); p.mouse.down()
    for pt in part: p.mouse.move(*pt)
    prog2 = p.evaluate('LT.prog')
    p.mouse.move(part[-1][0] + 160, part[-1][1] + 160, steps=4); p.wait_for_timeout(350); p.mouse.move(part[-1][0] + 165, part[-1][1] + 170, steps=2)
    said = p.text_content('#lSay')
    check(f'off the line: progress stops at {prog2:.0f} ({p.evaluate("LT.prog"):.0f}) and says "Back to the line." (said "{said}")', abs(p.evaluate('LT.prog') - prog2) < 1 and 'line' in said)
    p.mouse.up(); p.wait_for_timeout(200)
    check('lifting the finger mid-letter shows a green dot where to carry on', p.eval_on_selector_all('#tSvg .start', 'e => e.length') == 1)
    # carry on to the end
    cur = p.evaluate('LT.prog')
    rest = screen_pts(p, 0, frm=cur)
    p.mouse.move(*screen_pts(p, 0, upto=cur)[-1]); p.mouse.down()
    for pt in rest: p.mouse.move(*pt)
    p.mouse.up(); p.wait_for_timeout(300)
    check('finishing the a: letter done, green, says the sound and the word', p.evaluate('LT.done') and p.evaluate("$('tSvg').classList.contains('done')"))
    p.wait_for_timeout(1500)
    p.screenshot(path=OUT / 'l3_done.png')
    check('the a is remembered as traced, and the line gets a little stricter next time', p.evaluate('lstore.traced.a') == 1)
    tol1 = p.evaluate('LT.tolBase'); p.click('#tAgainL'); p.wait_for_timeout(200); tol2 = p.evaluate('LT.tolBase')
    check(f'stricter: {tol1} -> {tol2} units', tol2 < tol1)
    # stroke order: t's cross can't come first
    p.evaluate('setLetter("t")'); skip_demo(p)
    trace_stroke(p, 1)
    check('t: the cross before the down stroke does nothing', p.evaluate('LT.k') == 0 and p.evaluate('LT.prog') == 0)
    p.wait_for_timeout(2600)
    trace_stroke(p, 0); trace_stroke(p, 1)
    check('t: down, then across, is done', p.evaluate('LT.done'))
    # every letter, a to z, traced the way a finger would
    failed = [ch for ch in 'abcdefghijklmnopqrstuvwxyz' if not trace_letter(p, ch)]
    check(f'all 26 letters can be traced start to finish{": failed " + str(failed) if failed else ""}', not failed)
    # the family's pictures: family words
    p.evaluate('setLetter("d")'); skip_demo(p)
    check(f'in a family browser, d is for Dad ({p.get_attribute("#tPic img", "src")})', p.get_attribute('#tPic img', 'src').endswith('letters/fam/dad.webp') and p.text_content('#tWord') == 'Dad')
    p.click('#tPickOpen'); p.click('#tPick button[data-ch="x"]'); skip_demo(p)
    check('the letter picker jumps to x (box, with the x at the end)', p.evaluate('LT.ch') == 'x' and p.inner_html('#tWord') == 'bo<b>x</b>')
    # ---------------------------------------------------------------- spell
    p.click('#lmSpell'); p.wait_for_timeout(300)
    check('Spell shows 4 levels (with My name)', p.eval_on_selector_all('#sLevels .level', 'e => e.length') == 4)
    def spell_word(right=True):
        letters = p.evaluate('LS.letters')
        for c in letters:
            p.locator(f'#sTiles .tile:not(.used)[data-ch="{c}"]').first.click(); p.wait_for_timeout(60)
        return letters
    for lvl in range(3):
        p.click(f'#sLevels .level >> nth={lvl}'); p.wait_for_timeout(300)
        n = p.evaluate('LS.letters.length'); tiles = p.eval_on_selector_all('#sTiles .tile', 'e => e.length')
        ghosts = p.evaluate("[...document.querySelectorAll('#sSlots .slot')].map(s => s.textContent).join('')")
        want_tiles = n + (2 if lvl == 2 else 0)
        check(f'level {lvl + 1}: "{p.evaluate("LS.letters.join(\'\')")}" has {n} slots, {tiles} tiles (want {want_tiles}), ghost letters {"shown" if ghosts else "hidden"}',
              tiles == want_tiles and (bool(ghosts) == (lvl == 0)) and (n == 3 if lvl == 0 else n == 4 if lvl == 1 else n in (3, 4)))
        if lvl == 0:
            # a wrong letter shakes and stays
            wrong = p.evaluate("(() => { const need = LS.letters[0]; const t = [...document.querySelectorAll('#sTiles .tile')].find(t => t.dataset.ch !== need); return t ? t.dataset.ch : null; })()")
            p.locator(f'#sTiles .tile[data-ch="{wrong}"]').first.click(); p.wait_for_timeout(100)
            check(f'tapping "{wrong}" first shakes it and leaves the slots empty', p.evaluate('LS.filled') == 0 and p.eval_on_selector_all('#sTiles .tile.nope', 'e => e.length') == 1)
        spell_word()
        p.wait_for_function("!$('sNext').hidden", timeout=15000)
        check(f'level {lvl + 1}: spelled, sounded out, "Next word" shows', p.evaluate('LS.filled === LS.letters.length') and p.eval_on_selector_all('#sSlots .slot.filled', 'e => e.length') == n)
        if lvl == 0: p.screenshot(path=OUT / 'l4_spelled.png')
        p.click('#sNext'); p.wait_for_timeout(200)
        check(f'level {lvl + 1}: Next word gives a different word', p.evaluate('LS.filled') == 0)
    p.click('#sLevels .level >> nth=3'); p.wait_for_timeout(300)
    check(f'My name: {"-".join(KID)} with the letters showing', p.evaluate("LS.letters.join('')") == KID and p.evaluate("[...document.querySelectorAll('#sSlots .slot')].map(s => s.textContent).join('')") == KID)
    spell_word(); p.wait_for_function("!$('sNext').hidden", timeout=15000)
    check('My name spelled', p.evaluate('LS.filled') == len(KID))
    p.screenshot(path=OUT / 'l5_name.png')
    # leaving stops everything
    p.click('#lettergame [data-go="home"]'); p.wait_for_timeout(200)
    check('leaving Letters stops the voice and the demo', not p.evaluate('LT.demoing') and p.evaluate('LS.busy') in (False, None))
    p.goto(BASE + f'?for={KID}#letters'); p.wait_for_timeout(500)
    check('it remembers the mode (opens on Spell again)', p.is_visible('#spellBox'))

    # ---------------------------------------------------------------- sound hunt and first sounds
    def play_round(label, first_wrong=True):
        for k in range(10):
            p.wait_for_function(f"!LH.busy && LH.n === {k} && document.querySelectorAll('#hTiles .tile').length > 0", timeout=15000)
            t = p.evaluate('LH.target')
            if k == 0 and first_wrong:
                wrong = p.evaluate("[...document.querySelectorAll('#hTiles .tile')].map(b => b.dataset.ch).find(c => c !== LH.target)")
                p.click(f'#hTiles .tile[data-ch="{wrong}"]'); p.wait_for_timeout(120)
                check(f'{label}: a wrong letter shakes and the question stays', p.evaluate('LH.n') == 0 and p.eval_on_selector_all('#hTiles .tile.nope', 'e => e.length') == 1 and not p.evaluate('LH.res[0]'))
            p.click(f'#hTiles .tile[data-ch="{t}"]')
        p.wait_for_function("!$('hEnd').hidden", timeout=20000)
        res = p.evaluate('LH.res')
        check(f'{label}: a round is 10, ending on "Play again" with the dots ({"".join("x" if r == "miss" else "o" for r in res)})',
              len(res) == 10 and res[0] == ('miss' if first_wrong else 'hit') and all(r == 'hit' for r in res[1:]) and p.is_visible('#hAgain'))

    p.click('#lmHunt'); p.wait_for_timeout(400)
    check('Sounds: two levels, the speaker, 3 letters, 10 dots', p.is_visible('#huntBox') and p.eval_on_selector_all('#hLevels .level', 'e => e.length') == 2
          and p.is_visible('#hHear') and not p.is_visible('#hPic') and p.eval_on_selector_all('#hTiles .tile', 'e => e.length') == 3 and p.eval_on_selector_all('#hDots i', 'e => e.length') == 10)
    check('Sounds: the answer is there exactly once', p.evaluate("[...document.querySelectorAll('#hTiles .tile')].filter(b => b.dataset.ch === LH.target).length") == 1)
    rules = p.evaluate('''() => { const out = { easy: [], tricky: [] }; const L = 'abcdefghijklmnopqrstuvwxyz'.split('');
        for (const [lvl, key] of [['1', 'easy'], ['2', 'tricky']]) { LH.level = lvl;
          for (let r = 0; r < 40; r++) for (const t of L) { const c = huntChoices(t);
            const close = new Set([...(LH_NEAR[t] || '')]); for (const k in LH_NEAR) if (LH_NEAR[k].includes(t)) close.add(k);
            const bad = new Set(c).size !== c.length || !c.includes(t) || (c.includes('c') && c.includes('k')) || c.some(x => x === 'x' && t !== 'x')
              || c.length !== (lvl === '2' ? 4 : 3) || (lvl === '1' && c.some(x => x !== t && close.has(x)))
              || (lvl === '2' && (LH_NEAR[t] || '').length && !c.some(x => (LH_NEAR[t] || '').includes(x) && x !== t) && ![...(LH_NEAR[t] || '')].every(x => x === 'x' || (LH_SAME[t] === x)));
            if (bad) out[key].push(t + ':' + c.join('')); } }
        LH.level = '1'; return out; }''')
    check(f'Sounds, Easy: never a look- or sound-alike, never c with k (2 x 1040 rounds) {rules["easy"][:3]}', not rules['easy'])
    check(f'Sounds, Tricky: 4 letters, always one look- or sound-alike, never c with k {rules["tricky"][:3]}', not rules['tricky'])
    play_round('Sounds')
    p.screenshot(path=OUT / 'l7_sounds_end.png')
    p.click('#hAgain'); p.wait_for_timeout(300)
    check('Play again starts a new round', p.evaluate('LH.n') == 0 and p.is_visible('#hTiles') and p.evaluate('LH.res.length') == 0)
    p.click('#hLevels .level >> nth=1'); p.wait_for_timeout(300)
    sz = p.evaluate("[...document.querySelectorAll('#hTiles .tile')].map(b => Math.round(b.getBoundingClientRect().width))")
    rows = p.evaluate("new Set([...document.querySelectorAll('#hTiles .tile')].map(b => Math.round(b.getBoundingClientRect().top))).size")
    check(f'Sounds, Tricky on a phone: 4 letters in a 2 x 2, each {sz[0] if sz else 0} px (2 cm is about 76)', len(sz) == 4 and min(sz) >= 84 and rows == 2)
    p.screenshot(path=OUT / 'l8_sounds_tricky.png')

    p.click('#lmFirst'); p.wait_for_timeout(400)
    p.wait_for_function("$('hPic').querySelector('img').complete", timeout=5000)
    check('First sound: a picture instead of the speaker', p.is_visible('#hPic') and not p.is_visible('#hHear') and p.evaluate("$('hPic').querySelector('img').naturalWidth") > 0)
    q = p.evaluate("LH.queue.map(w => LETTER_DATA.words[w].text)")
    firsts = [w[0].lower() for w in q]
    check(f'First sound: 10 words with 10 different first letters, none on x ({", ".join(q)})', len(q) == 10 and len(set(firsts)) == 10 and 'x' not in firsts)
    check('First sound: the answer is the word\'s first letter', p.evaluate("LH.target === LH.word.text[0].toLowerCase()"))
    pool = p.evaluate("Object.keys(LETTER_DATA.words).filter(w => familyDevice() || !LETTER_DATA.words[w].pic.startsWith('family:'))")
    check('First sound in a family browser can use the family words', not FAM_IDS or FAM_IDS <= set(pool))
    play_round('First sound', first_wrong=False)
    p.goto(BASE + f'?for={KID}&again=1#letters'); p.wait_for_function("!$('huntBox').hidden && LH.queue.length === 10", timeout=8000)
    check('it remembers the mode (opens on First sound again)', p.is_visible('#huntBox') and p.is_visible('#hPic'))
    p.screenshot(path=OUT / 'l9_first.png')
    ctx.close()

    # ---------------------------------------------------------------- a device without the pass
    ctx, p = page_at(b, 390, 844, passed=False)
    p.goto(BASE + '?for=Max'); p.wait_for_timeout(400)
    check('without the pass: the Letters tile and heading are hidden, Numbers is there', not p.is_visible('#playLetters') and not p.is_visible('#lettersHead') and p.is_visible('#playCount'))
    p.goto(BASE + '?for=Max#letters'); p.wait_for_timeout(400)
    check('without the pass: #letters opens the Learning Lab\'s games instead', p.is_visible('#home') and not p.is_visible('#lettergame'))
    reqs = []
    p.on('request', lambda r: '/letters/' in r.url and reqs.append(r.url))
    p.evaluate('loadFamily()'); p.wait_for_timeout(300)
    check('without the pass: the family words are never asked for, whatever the name', not reqs and p.evaluate('FAMILY') is None and not p.evaluate('famOn()'))
    ctx.close()

    # ---------------------------------------------------------------- the real recordings
    vi = Path(SITE / 'letters' / 'voices' / 'index.json')
    if vi.exists() and any(json.loads(vi.read_text()).values()):
        ctx, p = page_at(b, 390, 844, voices='real')
        p.goto(BASE + f'?for={KID}#letters'); p.wait_for_timeout(500); skip_demo(p)
        idx = json.loads(vi.read_text())
        tools = SITE.parent / 'letters'
        all_ids = []
        for f in ('letters_data.json', 'letters_family.json'):
            if (tools / f).exists(): all_ids += [c['id'] for c in json.loads((tools / f).read_text())['clips'] if not c.get('optional')]
        missing = [i for i in all_ids if i not in idx['mum'] and i not in idx['dad']]
        check(f'real voices: every clip recorded by one of them ({len(all_ids) - len(missing)} of {len(all_ids)})', not missing)
        bad = p.evaluate('''async idx => { const out = []; for (const v of ['mum', 'dad']) for (const id of idx[v]) {
            const r = await fetch(`letters/voices/${v}/${id}.mp3`); if (!r.ok) out.push(v + '/' + id); } return out; }''', idx)
        check('real voices: every listed clip is there', not bad)
        res = p.evaluate('''async () => { await voice.load(); const out = {};
            for (const w of ['mum', 'dad']) { while (voice.who !== w) voice.nextVoice();
              out[w] = ['sound_f', 'word_fox', 'say_watch', 'name_e'].map(id => voice.has(id)); }
            return out; }''')
        check('real voices: in a Mum round and a Dad round, the sounds and the words are both there', all(res['mum']) and all(res['dad']))
        dec = p.evaluate('''async () => { while (voice.who !== 'dad') voice.nextVoice(); sound.on = true;
            const t = performance.now(); const ok = await voice.say([['sound_f', 'f'], ['word_fox', 'fox']], 50); return [ok, performance.now() - t]; }''')
        check(f'real voices: a Dad round plays Mum\'s "f" then Dad\'s "fox" ({dec[1]:.0f} ms)', dec[0] and dec[1] > 600)
        ctx.close()

    # ---------------------------------------------------------------- a gift copy (no family file on its site): no family pictures or words
    page_src = (SITE / 'index.html').read_text(encoding='utf-8')
    fam = SITE / 'letters' / 'family.json'
    fam_words = [w['text'] for w in json.loads(fam.read_text())['words'].values()] if fam.exists() else []
    check('the page itself carries no family words (they load from letters/family.json, behind the lock)',
          not [t for t in fam_words if t in page_src and t not in ('Mum', 'Dad')] and '"family:' not in page_src)
    ctx, p = page_at(b, 390, 844)
    ctx.route('**/letters/family.json', lambda r: r.fulfill(status=404, body='not found'))
    fam_reqs = []
    p.on('request', lambda r: 'family.json' in r.url and fam_reqs.append(r.url))
    p.goto(BASE + '?for=Max#letters'); p.wait_for_timeout(500); skip_demo(p)
    check('no recorded voice: words show instead, nothing breaks', p.evaluate('voice.who') is None)
    p.evaluate('setLetter("d")'); skip_demo(p)
    p.evaluate("letterMode('first')"); p.wait_for_timeout(300)
    gq = p.evaluate("LH.queue")
    no_fam = not set(gq) & FAM_IDS and not p.evaluate("LH.queue.some(w => LETTER_DATA.words[w].pic.startsWith('family:'))")
    check(f'a gift copy\'s First sound has no family words ({", ".join(gq)})', no_fam and len(gq) == 10)
    p.evaluate("letterMode('trace')"); p.wait_for_timeout(200)
    check(f'a gift copy asks for the family file at most once, finds none and carries on ({len(fam_reqs)} asks)', len(fam_reqs) <= 1 and p.evaluate('FAMILY') is False)
    check(f'for Max, d is for dragon (not Dad)', 'faces/F24' in p.get_attribute('#tPic img', 'src') and p.text_content('#tWord') == 'dragon')
    p.evaluate('setLetter("p")'); skip_demo(p)
    check('for Max, p is for penguin', p.text_content('#tWord') == 'penguin')
    p.click('#lmSpell'); p.wait_for_timeout(300)
    pool = p.evaluate("(() => { const seen = new Set(); for (let i = 0; i < 60; i++) { LS.level = '1'; seen.add(pickWord().id); } return [...seen]; })()")
    check(f'for Max, no Mum or Dad words in spelling ({len(pool)} words seen)', 'mum' not in pool and 'dad' not in pool)
    p.click('#sLevels .level >> nth=3'); p.wait_for_timeout(300)
    check('My name for Max: M-a-x, with no family picture', p.evaluate("LS.letters.join('')") == 'Max' and p.evaluate('LS.word.pic') is None)
    ctx.close()

    # ---------------------------------------------------------------- My name's picture comes from the family words, not the code
    # a stand-in family file with one made-up name, so the real names stay out of this test
    stand_in = {'letters': {}, 'words': {'sam': {'text': 'Sam', 'pic': 'family:sam'}}, 'spell': {}}
    face = (SITE / 'faces' / 'F01.webp').read_bytes()
    for who, want in (('Sam', 'family:sam'), ('Max', None)):
        ctx, p = page_at(b, 390, 844)
        ctx.route('**/letters/family.json', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(stand_in)))
        ctx.route('**/letters/fam/*.webp', lambda r: r.fulfill(status=200, content_type='image/webp', body=face))
        p.goto(BASE + f'?for={who}#letters'); p.wait_for_timeout(500); skip_demo(p)
        p.click('#lmSpell'); p.wait_for_timeout(300)
        p.click('#sLevels .level >> nth=3'); p.wait_for_timeout(300)
        src = p.get_attribute('#sPic img', 'src')
        check(f'My name for {who}: picture {p.evaluate("LS.word.pic")} ({src})', p.evaluate('LS.word.pic') == want
              and (src.endswith('letters/fam/sam.webp') if want else src.endswith('faces/F01.webp')))
        ctx.close()

    # ---------------------------------------------------------------- other sizes
    for (w, h, touch, label) in ((360, 740, True, 'small phone'), (904, 1000, True, 'folding phone open'), (1280, 800, False, 'laptop')):
        ctx, p = page_at(b, w, h, touch)
        p.goto(BASE + f'?for={KID}#letters'); p.wait_for_timeout(900); skip_demo(p)
        check(f'{label} {w}px: no sideways scroll', not p.evaluate('document.documentElement.scrollWidth > innerWidth'))
        r = p.locator('#tSvg').bounding_box()
        check(f'{label}: the tracing area is on screen ({r["y"]:.0f}-{r["y"] + r["height"]:.0f} of {h}, {r["width"]:.0f} wide)', r['y'] >= 0 and r['y'] + r['height'] <= h + 1)
        check(f'{label}: e traced', trace_letter(p, 'e'))
        p.screenshot(path=OUT / f'l6_{w}.png')
        p.click('#lmSpell'); p.wait_for_timeout(300)
        check(f'{label}: spell screen fits ({p.evaluate("document.documentElement.scrollWidth")} px wide)', not p.evaluate('document.documentElement.scrollWidth > innerWidth'))
        ctx.close()
    b.close()
srv.shutdown(); shutil.rmtree(TMP, ignore_errors=True)
print('PROBLEMS:' if problems else 'all good', *problems, sep='\n  ')
