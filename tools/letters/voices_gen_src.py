"""Letters game voices, made with Gemini text-to-speech instead of recording them.

    py voices_gen.py samples            find Australian voices, make a few test clips in each, then open
                                        voice_samples/listen.html to compare them (what 'Voice samples.bat' runs)
    py voices_gen.py all W1 M2          make every clip in the two voices picked from the samples
                                        -> voices/mum (first pick) and voices/dad (second pick)
    py voices_gen.py redo sound_b ...   remake just those clips in both picked voices (old ones go to voices/_old)
    py voices_gen.py check              is the key set? (no API call)

Options:
    --model gemini-3.8-flash-tts        speech model (default; gemini-3.8-flash-lite-tts is cheaper)

The API key is read from the GEMINI_API_KEY environment variable. Nothing needs installing: this uses
Python's own web library. Everything that happens is written to voice_samples/log.txt.
"""
import argparse, base64, io, json, os, re, shutil, struct, sys, time, wave
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / 'voice_samples'
VOICES = HERE / 'voices'
API = os.environ.get('GEN_API_BASE', 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')

LETTER_NAMES = {}   # filled in by the build step: letter -> name as said in Australia
LETTER_TIPS = {}    # filled in by the build step: letter -> what the sound should be
WORDS = {}          # filled in by the build step: word id -> how it's written
PROMPTS = {}        # filled in by the build step: prompt id -> what's said

# What the speech model is given to say for each letter sound. It reads text out loud, so a bare "b" risks "bee";
# the style line below asks for the clipped sound. The samples test the tricky ones (see SOUND_TEST).
SOUND_TTS = {'a': 'a', 'b': 'b', 'c': 'k', 'd': 'd', 'e': 'e', 'f': 'fff', 'g': 'g', 'h': 'h', 'i': 'i', 'j': 'j',
             'k': 'k', 'l': 'lll', 'm': 'mmm', 'n': 'nnn', 'o': 'o', 'p': 'p', 'q': 'kw', 'r': 'rrr', 's': 'sss',
             't': 't', 'u': 'u', 'v': 'vvv', 'w': 'w', 'x': 'ks', 'y': 'y', 'z': 'zzz'}
NAME_TTS = {'g': 'gee', 'q': 'queue'}      # spelled so the reader can't mistake them; others use LETTER_NAMES
PRAISE = {'well_done', 'did_it', 'great_writing', 'great_spelling'}

STYLE = {
    'sound': ('Say only this one short phonics letter sound, the way a teacher teaches letter sounds to a '
              'young child: quick and clipped, with no extra "uh" after it, and nothing else.'),
    'name': 'Say the name of this letter of the alphabet clearly, the way Australians say it.',
    'word': 'Say this one word clearly and warmly, like reading an alphabet book to a young child.',
    'prompt': 'Warm, kind and encouraging, speaking to a young child.',
    'praise': 'Delighted and proud, cheering on a young child.',
}

# Voices to design if Google's library has no Australian ones (or only one of a kind). Same wording for both.
DESIGNS = [
    ('warm', 'A warm, gentle Australian {who} in {their} thirties with a natural Sydney accent, speaking clearly '
             'and kindly, like a parent reading a picture book to a young child.'),
    ('bright', 'A bright, cheerful Australian {who} in {their} thirties with a natural Sydney accent, playful '
               'and upbeat, like a favourite preschool teacher.'),
]
PREBUILT = {'woman': ['Sulafat', 'Vindemiatrix'], 'man': ['Achird', 'Umbriel']}   # last resort
KINDS = {'woman': ('W', 'female', 'woman', 'her'), 'man': ('M', 'male', 'man', 'his')}

SAMPLE_CLIPS = ['sound_a', 'sound_b', 'sound_m', 'sound_t', 'name_h', 'name_z', 'word_fox', 'word_uncle',
                'say_watch', 'say_great_spelling']
SOUND_TEST = [('a', 'ah'), ('a', 'æ'), ('b', 'buh'), ('b', '/b/'), ('t', 'tuh'), ('t', '/t/')]


# ---------- the clip list ----------

def clips():
    out = []
    for ch in LETTER_NAMES:
        out.append({'id': f'sound_{ch}', 'kind': 'sound', 'text': SOUND_TTS[ch]})
    for ch, name in LETTER_NAMES.items():
        out.append({'id': f'name_{ch}', 'kind': 'name', 'text': NAME_TTS.get(ch, name)})
    for w, text in WORDS.items():
        out.append({'id': f'word_{w}', 'kind': 'word', 'text': text})
    for k, text in PROMPTS.items():
        out.append({'id': f'say_{k}', 'kind': 'praise' if k in PRAISE else 'prompt', 'text': text})
    return out

CLIP = {}

def label(cid):
    kind, key = cid.split('_', 1)
    if kind == 'sound': return f'Sound "{key}": {LETTER_TIPS.get(key, "")}'
    if kind == 'name': return f'Letter name "{LETTER_NAMES.get(key, key)}"'
    if kind == 'word': return f'Word "{WORDS.get(key, key)}"'
    return f'"{PROMPTS.get(key, key)}"'


# ---------- talking to the API ----------

class ApiError(Exception):
    def __init__(self, code, body):
        super().__init__(f'HTTP {code}: {body[:400]}'); self.code = code; self.body = body

def log(msg):
    SAMPLES.mkdir(exist_ok=True)
    with (SAMPLES / 'log.txt').open('a', encoding='utf-8') as f:
        f.write(f'{datetime.now().isoformat(timespec="seconds")}  {msg}\n')

def key():
    k = os.environ.get('GEMINI_API_KEY')
    if not k: sys.exit('GEMINI_API_KEY is not set. Run:  setx GEMINI_API_KEY "your-key"  then open a new window.')
    return k

def call(method, path, body=None, query=None):
    url = API + path + ('?' + urlencode(query, doseq=True) if query else '')
    data = json.dumps(body).encode('utf-8') if body is not None else None
    for attempt in range(4):
        req = Request(url, data=data, method=method,
                      headers={'x-goog-api-key': key(), 'Content-Type': 'application/json'})
        try:
            with urlopen(req, timeout=180) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except HTTPError as e:
            text = e.read().decode('utf-8', 'replace')
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                wait = 20 * (attempt + 1)
                print(f'    busy ({e.code}), waiting {wait} s'); log(f'{method} {path} busy {e.code}: {text[:200]}')
                time.sleep(wait); continue
            log(f'{method} {path} failed {e.code}: {text[:1500]}')
            raise ApiError(e.code, text)
        except URLError as e:
            if attempt < 3:
                print(f'    no connection ({e.reason}), trying again in 10 s'); time.sleep(10); continue
            raise ApiError(0, f'no connection: {e.reason}')

def g(d, *names):
    """First present field, in either snake_case or camelCase."""
    for n in names:
        for k in (n, re.sub(r'_(\w)', lambda m: m.group(1).upper(), n)):
            if isinstance(d, dict) and d.get(k) not in (None, '', []): return d[k]
    return None

def voice_id(v):
    vid = g(v, 'id') or g(v, 'voice_id') or g(v, 'name') or ''
    if not isinstance(vid, str) or vid.startswith('operations/'): return ''
    return vid.split('/')[-1]

def find_audio(obj):
    """The last base64 audio block anywhere in a response (steps[].content[] in the docs; output_audio in the SDK)."""
    found = []
    def walk(o):
        if isinstance(o, dict):
            mt = str(g(o, 'mime_type') or '')
            if isinstance(o.get('data'), str) and (o.get('type') == 'audio' or mt.startswith('audio')):
                found.append((o['data'], mt))
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(obj)
    return found[-1] if found else (None, None)

def shape(o, depth=0):
    """Keys only, for the log when a response isn't what we expected."""
    if depth > 4: return '...'
    if isinstance(o, dict): return {k: shape(v, depth + 1) for k, v in o.items()}
    if isinstance(o, list): return [shape(o[0], depth + 1)] if o else []
    return type(o).__name__

def to_wav(data, mime):
    if data[:4] == b'RIFF': return data
    rate = int((re.search(r'rate=(\d+)', mime or '') or [0, 24000])[1])
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(data)
    return buf.getvalue()

STATE = {'style': True}

def speak(model, vid, text, style):
    content = {'type': 'text', 'text': text}
    if STATE['style'] and style:
        content['annotations'] = [{'type': 'speech_metadata', 'style': style}]
    body = {'model': model, 'input': [{'type': 'user_input', 'content': [content]}],
            'response_format': {'type': 'audio'}, 'generation_config': {'speech_config': [{'voice': vid}]}}
    try:
        r = call('POST', '/interactions', body)
    except ApiError as e:
        if e.code == 400 and STATE['style'] and re.search(r'annotation|speech_metadata|style', e.body, re.I):
            print('    the model refused the style line; carrying on without it'); log('style off: ' + e.body[:300])
            STATE['style'] = False
            return speak(model, vid, text, None)
        raise
    data, mime = find_audio(r)
    if not data:
        log('no audio in response: ' + json.dumps(shape(r))[:1500])
        raise ApiError(200, 'no audio came back (details in voice_samples/log.txt)')
    return to_wav(base64.b64decode(data), mime)


# ---------- choosing voices ----------

def library(model):
    """Google's prebuilt voices tagged Australian English."""
    seen, out = set(), []
    for q in ({'language_code': 'en-AU'}, {'accent': 'Australian'}):
        try:
            r = call('GET', '/voices', query={**q, 'type': 'prebuilt', 'page_size': 200})
        except ApiError as e:
            print(f'    could not list voices ({str(e)[:120]})'); continue
        for v in g(r, 'voices') or []:
            vid = voice_id(v)
            if vid and vid not in seen:
                seen.add(vid); out.append(v)
    (SAMPLES / 'voices_found.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    return out

def design(model, kind, style, about):
    letter, gender, who, their = KINDS[kind]
    text = about.format(who=who, their=their)
    body = {'store': True, 'voice': {'model': model, 'type': 'prompted', 'display_name': f'Letters {kind} ({style})',
                                     'gender': gender, 'language_code': 'en-AU', 'prompted': {'input': text}}}
    try:
        r = call('POST', '/voices', body)
    except ApiError as e:
        if e.code != 400: raise
        body['voice'].pop('language_code'); r = call('POST', '/voices', body)   # en-AU not accepted as a tag
    v = g(r, 'voice') if g(r, 'voice') and not voice_id(r) else r
    vid = voice_id(v)
    if not vid:
        log('voice design response without an id: ' + json.dumps(shape(r))[:1500])
        raise ApiError(200, 'the designed voice came back without an id')
    return vid, text

def choose(model):
    SAMPLES.mkdir(exist_ok=True)
    print('Looking for Australian voices...')
    lib = library(model); chosen = []
    print(f'  {len(lib)} Australian voice(s) in Google\'s library')
    for kind in ('woman', 'man'):
        letter, gender, who, their = KINDS[kind]
        picks = [v for v in lib if str(g(v, 'gender') or '').lower() == gender][:2]
        for v in picks:
            chosen.append({'kind': kind, 'id': voice_id(v), 'source': 'library',
                           'about': f'{g(v, "display_name") or voice_id(v)}: {g(v, "description") or ""}'.strip(': ')})
        for style, about in DESIGNS[:2 - len(picks)]:
            print(f'  designing an Australian {who}\'s voice ({style})...')
            try:
                vid, text = design(model, kind, style, about)
                chosen.append({'kind': kind, 'id': vid, 'source': 'designed', 'description': text,
                               'about': f'Designed for this: {"warm and gentle" if style == "warm" else "bright and cheerful"}'})
            except ApiError as e:
                print(f'    could not design it ({str(e)[:160]})')
        for name in PREBUILT[kind]:
            if sum(c['kind'] == kind for c in chosen) >= 2: break
            print(f'  using Google\'s "{name}" voice instead (not Australian)')
            chosen.append({'kind': kind, 'id': name, 'source': 'prebuilt', 'about': f'{name} (Google voice, not Australian)'})
        n = 0
        for c in chosen:
            if c['kind'] == kind and 'label' not in c:
                n += 1; c['label'] = f'{letter}{n}'
    (SAMPLES / 'voices.json').write_text(json.dumps(chosen, indent=1, ensure_ascii=False), encoding='utf-8')
    log('voices: ' + ', '.join(f'{c["label"]}={c["id"]} ({c["source"]})' for c in chosen))
    return chosen


# ---------- the listening page ----------

PAGE = """<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><title>Letters voice samples</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{font:16px/1.45 system-ui,sans-serif;margin:24px auto;max-width:1000px;padding:0 16px;color:#222;background:#fffaf2}
h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:28px 0 8px} p{margin:6px 0 12px;max-width:70ch}
table{border-collapse:collapse;width:100%;background:#fff} th,td{border:1px solid #e3d9c8;padding:8px;text-align:left;vertical-align:top}
th{background:#f6eee0;font-weight:600} td.c{text-align:center;width:90px} .about{font-weight:400;font-size:13px;color:#555}
button{font:inherit;font-size:18px;width:52px;height:40px;border-radius:10px;border:1px solid #c9b79a;background:#fff;cursor:pointer}
.wrap{overflow-x:auto} button:hover{background:#f6eee0} button.on{background:#ffd98a} .none{color:#aaa}
</style></head><body>
<h1>Letters voice samples</h1>
<p>Press &#9654; to hear each one. Pick one woman's voice and one man's voice for the game, then tell Claude
which (for example "W1 and M2"), plus anything that sounds wrong.</p>
<p>Listen hardest to the letter sounds: "b" and "t" should be short and clipped, with no "buh" or "tuh" on the end,
and "a" should be the "a" in ant, not "ay".</p>
%TABLES%
<script>
let cur=null,btn=null;
document.querySelectorAll('button[data-src]').forEach(b=>b.onclick=()=>{
 if(cur){cur.pause();btn.classList.remove('on')}
 cur=new Audio(b.dataset.src+'?'+Date.now());btn=b;b.classList.add('on');
 cur.onended=()=>b.classList.remove('on');cur.play();
});
</script></body></html>"""

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def cell(path):
    if path.exists(): return f'<td class="c"><button data-src="{esc(path.relative_to(SAMPLES).as_posix())}">&#9654;</button></td>'
    return '<td class="c none">&ndash;</td>'

def write_page(chosen):
    head = '<tr><th>Clip</th>' + ''.join(f'<th>{c["label"]}<div class="about">{esc(c["about"])}</div></th>' for c in chosen) + '</tr>'
    rows = ''.join(f'<tr><td>{esc(label(cid))}</td>' + ''.join(cell(SAMPLES / c['label'] / f'{cid}.wav') for c in chosen) + '</tr>'
                   for cid in SAMPLE_CLIPS)
    t1 = f'<h2>The voices</h2><div class="wrap"><table>{head}{rows}</table></div>'
    firsts = [c for c in chosen if c['label'] in ('W1', 'M1')]
    head2 = '<tr><th>Letter sound, written as</th>' + ''.join(f'<th>{c["label"]}</th>' for c in firsts) + '</tr>'
    rows2 = ''
    for ch in ('a', 'b', 't'):
        tests = [(SOUND_TTS[ch], f'sound_{ch}')] + [(t, test_name(ch, i)) for i, (c2, t) in enumerate(SOUND_TEST) if c2 == ch]
        for n, (text, stem) in enumerate(tests):
            tip = f' <span class="about">({esc(LETTER_TIPS.get(ch, ""))})</span>' if n == 0 else ''
            rows2 += f'<tr><td><b>{ch}{n + 1}</b> written "{esc(text)}"{tip}</td>'
            rows2 += ''.join(cell(SAMPLES / c['label'] / f'{stem}.wav') for c in firsts) + '</tr>'
    t2 = (f'<h2>Letter sounds test</h2><p>The same sounds written different ways, to find which way the voice gets right. '
          f'Line 1 of each is the one in the table above. Tell Claude which line sounds most like the real letter sound '
          f'(for example "b3").</p><div class="wrap"><table>{head2}{rows2}</table></div>')
    (SAMPLES / 'listen.html').write_text(PAGE.replace('%TABLES%', t1 + t2), encoding='utf-8')

def test_name(ch, i):
    return f'test_{ch}_{i + 1}'


# ---------- commands ----------

def make(model, vid, cid, path, text=None, kind=None):
    c = CLIP[cid]
    data = speak(model, vid, text or c['text'], STYLE[kind or c['kind']])
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    with wave.open(str(path)) as w: secs = w.getnframes() / w.getframerate()
    log(f'made {path.relative_to(HERE).as_posix()} {secs:.2f}s ({text or c["text"]!r})')
    return secs

def samples(model):
    f = SAMPLES / 'voices.json'
    chosen = json.loads(f.read_text(encoding='utf-8')) if f.exists() else choose(model)
    print('\nVoices: ' + ', '.join(f'{c["label"]} ({c["source"]})' for c in chosen))
    jobs = [(c, cid, SAMPLES / c['label'] / f'{cid}.wav', None) for c in chosen for cid in SAMPLE_CLIPS]
    for c in chosen:
        if c['label'] in ('W1', 'M1'):
            for i, (ch, text) in enumerate(SOUND_TEST):
                jobs.append((c, f'sound_{ch}', SAMPLES / c['label'] / f'{test_name(ch, i)}.wav', text))
    todo = [j for j in jobs if not j[2].exists()]
    print(f'Making {len(todo)} sample clip(s) with {model}.' if todo else 'Every sample is made already.')
    ok = 0
    for c, cid, path, text in todo:
        try:
            secs = make(model, c['id'], cid, path, text)
            print(f'  {c["label"]} {path.stem}: {secs:.1f} s'); ok += 1
        except ApiError as e:
            print(f'  {c["label"]} {path.stem}: failed: {str(e)[:200]}')
            if e.code in (400, 401, 403, 404) and ok == 0:
                print('\nStopping: the first clips all failed the same way. The details are in voice_samples/log.txt.')
                break
    if todo and not ok:
        print('\nNothing was made, so there is nothing to listen to yet. Tell Claude what the window says.'); return
    write_page(chosen)
    print((f'\n{ok} of {len(todo)} made. ' if todo else '') + 'Opening voice_samples/listen.html.')

def picked():
    f = VOICES / 'picked.json'
    if not f.exists(): sys.exit('No voices picked yet. Run:  py voices_gen.py all W1 M1  (with the labels you liked)')
    return json.loads(f.read_text(encoding='utf-8'))

def full(model, labels, redo=None):
    if redo is None:
        chosen = {c['label']: c for c in json.loads((SAMPLES / 'voices.json').read_text(encoding='utf-8'))}
        if len(labels) != 2 or any(l.upper() not in chosen for l in labels):
            sys.exit(f'Name two voices from the samples, e.g.  py voices_gen.py all W1 M2  (have: {", ".join(chosen)})')
        pick = {'mum': chosen[labels[0].upper()], 'dad': chosen[labels[1].upper()]}
        VOICES.mkdir(exist_ok=True)
        (VOICES / 'picked.json').write_text(json.dumps(pick, indent=1, ensure_ascii=False), encoding='utf-8')
        ids = [c['id'] for c in clips()]
    else:
        pick = picked()
        bad = [i for i in redo if i not in CLIP]
        if bad: sys.exit(f'Unknown clip(s): {", ".join(bad)}. They look like sound_b, name_h, word_fox, say_watch.')
        ids = redo
    todo = []
    for slot, c in pick.items():
        for cid in ids:
            path = VOICES / slot / f'{cid}.wav'
            if redo is not None and path.exists():
                old = VOICES / '_old' / slot; old.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(old / f'{cid}_{datetime.now():%H%M%S}.wav'))
            if not path.exists(): todo.append((slot, c, cid, path))
    if not todo:
        print('Every clip is already made. To remake some:  py voices_gen.py redo sound_b name_h'); return
    print(f'Making {len(todo)} clip(s): {pick["mum"]["label"]} -> voices/mum, {pick["dad"]["label"]} -> voices/dad.')
    ok, failed = 0, []
    for i, (slot, c, cid, path) in enumerate(todo, 1):
        try:
            secs = make(model, c['id'], cid, path)
            print(f'  {i}/{len(todo)} {slot} {cid}: {secs:.1f} s'); ok += 1
        except ApiError as e:
            print(f'  {i}/{len(todo)} {slot} {cid}: failed: {str(e)[:200]}'); failed.append(cid)
            if e.code in (400, 401, 403, 404) and ok == 0 and len(failed) >= 3:
                print('\nStopping: the first clips all failed. The details are in voice_samples/log.txt.'); break
    print(f'\n{ok} of {len(todo)} made.' + (' Run it again to retry the ones that failed.' if failed else '') +
          ' Tell Claude when they are in.')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['samples', 'all', 'redo', 'check'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--model', default='gemini-3.8-flash-tts')
    a = ap.parse_args()
    CLIP.update({c['id']: c for c in clips()})
    for c in SAMPLE_CLIPS: assert c in CLIP, c
    if a.command == 'check':
        print('key:', 'set' if os.environ.get('GEMINI_API_KEY') else 'GEMINI_API_KEY not set in this window')
        print(f'{len(CLIP)} clips per voice; samples made: {len(list(SAMPLES.glob("*/*.wav")))}')
        return
    key()
    if a.command == 'samples': samples(a.model)
    elif a.command == 'all': full(a.model, a.args)
    else: full(a.model, [], redo=a.args)

if __name__ == '__main__':
    main()
