"""The maths games' narrator, made with Gemini text-to-speech.

    py number_voices.py              make every clip that isn't made yet (what 'Make number voices.bat' runs),
                                     then write listen.html to hear them all
    py number_voices.py redo n_4 ... make just those clips again (the old ones go to voices/_old)
    py number_voices.py --voice en-au-storyteller-4
                                     use a different voice: the clips made in the old one move to voices/_old,
                                     and every clip is made again
    py number_voices.py check        is the key set? (no API call)

The lines and the voice are in number_lines.json, next to this file. The API key is read from the
GEMINI_API_KEY environment variable. Nothing needs installing. Everything that happens goes into log.txt.
"""
import argparse, base64, io, json, os, re, shutil, sys, time, wave
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
OUT = HERE / 'voices' / 'narrator'
OLD = HERE / 'voices' / '_old'
API = os.environ.get('GEN_API_BASE', 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
DATA = json.loads((HERE / 'number_lines.json').read_text(encoding='utf-8'))
LINES = {l['id']: l for l in DATA['lines']}
PACE = float(os.environ.get('GEN_PACE', '6.5'))      # seconds between requests: the free tier allows 10 a minute


class ApiError(Exception):
    def __init__(self, code, body):
        super().__init__(f'HTTP {code}: {body[:300]}'); self.code = code; self.body = body

def log(msg):
    with (HERE / 'log.txt').open('a', encoding='utf-8') as f:
        f.write(f'{datetime.now().isoformat(timespec="seconds")}  {msg}\n')

def key():
    k = os.environ.get('GEMINI_API_KEY')
    if not k: sys.exit('GEMINI_API_KEY is not set. Run:  setx GEMINI_API_KEY "your-key"  then open a new window.')
    return k

def call(path, body):
    data = json.dumps(body).encode('utf-8')
    for attempt in range(5):
        req = Request(API + path, data=data, method='POST', headers={'x-goog-api-key': key(), 'Content-Type': 'application/json'})
        try:
            with urlopen(req, timeout=180) as r:
                return json.loads(r.read() or b'{}')
        except HTTPError as e:
            text = e.read().decode('utf-8', 'replace')
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                wait = 20 * (attempt + 1)
                print(f'    busy ({e.code}), waiting {wait} s'); log(f'busy {e.code}: {text[:200]}')
                time.sleep(wait); continue
            log(f'failed {e.code}: {text[:1500]}')
            raise ApiError(e.code, text)
        except URLError as e:
            if attempt < 4:
                print(f'    no connection ({e.reason}), trying again in 10 s'); time.sleep(10); continue
            raise ApiError(0, f'no connection: {e.reason}')

def g(d, name):
    camel = re.sub(r'_(\w)', lambda m: m.group(1).upper(), name)
    return d.get(name) if d.get(name) not in (None, '') else d.get(camel)

def find_audio(obj):
    """The last base64 audio block anywhere in the response."""
    found = []
    def walk(o):
        if isinstance(o, dict):
            mt = str(g(o, 'mime_type') or '')
            if isinstance(o.get('data'), str) and (o.get('type') == 'audio' or mt.startswith('audio')): found.append((o['data'], mt))
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(obj)
    return found[-1] if found else (None, None)

def to_wav(data, mime):
    if data[:4] == b'RIFF': return data
    rate = int((re.search(r'rate=(\d+)', mime or '') or [0, 24000])[1])
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(data)
    return buf.getvalue()

STATE = {'style': True}

def speak(model, voice, text, style):
    content = {'type': 'text', 'text': text}
    if STATE['style'] and style: content['annotations'] = [{'type': 'speech_metadata', 'style': style}]
    body = {'model': model, 'input': [{'type': 'user_input', 'content': [content]}],
            'response_format': {'type': 'audio'}, 'generation_config': {'speech_config': [{'voice': voice}]}}
    try:
        r = call('/interactions', body)
    except ApiError as e:
        if e.code == 400 and STATE['style'] and re.search(r'annotation|speech_metadata|style', e.body, re.I):
            print('    the model refused the style line; carrying on without it'); log('style off: ' + e.body[:300])
            STATE['style'] = False
            return speak(model, voice, text, None)
        raise
    data, mime = find_audio(r)
    if not data:
        log('no audio in response: ' + json.dumps(r)[:800])
        raise ApiError(200, 'no audio came back (details in log.txt)')
    return to_wav(base64.b64decode(data), mime)

def used_voice():
    f = OUT / 'voice.txt'
    return f.read_text(encoding='utf-8').strip() if f.exists() else None

def set_aside(ids):
    OLD.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    for i in ids:
        p = OUT / f'{i}.wav'
        if not p.exists(): continue
        dest, k = OLD / f'{i}.{stamp}.wav', 1
        while dest.exists(): k += 1; dest = OLD / f'{i}.{stamp}-{k}.wav'   # never overwrite an older take
        shutil.move(str(p), str(dest))

PAGE = """<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><title>Maths narrator</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{font:16px/1.45 system-ui,sans-serif;margin:24px auto;max-width:860px;padding:0 16px;color:#222;background:#fffaf2}
h1{font-size:24px;margin:0 0 6px} p{max-width:70ch} .grid{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}
button{font:inherit;padding:8px 12px;border-radius:10px;border:1px solid #c9b79a;background:#fff;cursor:pointer}
button.on{background:#ffd98a} .none{color:#aaa;border-style:dashed}
</style></head><body><h1>The maths games' narrator</h1>
<p>Voice: %VOICE%. Press each one to hear it. If the voice doesn't suit, or a line sounds wrong, tell Claude.</p>
<div class="grid">%BUTTONS%</div>
<script>let a=null,b=null;document.querySelectorAll('button[data-src]').forEach(x=>x.onclick=()=>{
if(a){a.pause();b.classList.remove('on')}a=new Audio(x.dataset.src+'?'+Date.now());b=x;x.classList.add('on');
a.onended=()=>x.classList.remove('on');a.play()});</script></body></html>"""

def esc(s): return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')

def write_page(voice):
    btns = ''
    for i, l in LINES.items():
        p = OUT / f'{i}.wav'
        btns += (f'<button data-src="voices/narrator/{i}.wav">{esc(l["text"])}</button>' if p.exists()
                 else f'<button class="none" disabled title="not made yet">{esc(l["text"])}</button>')
    (HERE / 'listen.html').write_text(PAGE.replace('%VOICE%', esc(voice)).replace('%BUTTONS%', btns), encoding='utf-8')

def make(model, voice, ids):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'voice.txt').write_text(voice + '\n', encoding='utf-8')
    done = failed = 0
    for n, i in enumerate(ids, 1):
        l = LINES[i]
        print(f'  [{n}/{len(ids)}] {l["text"]}')
        try:
            wav = speak(model, voice, l['text'], DATA['style'].get(l['kind']))
        except ApiError as e:
            print(f'    could not make it: {str(e)[:200]}'); failed += 1
            if e.code in (401, 403): sys.exit('The key was refused. Check GEMINI_API_KEY, then run this again.')
            continue
        (OUT / f'{i}.wav').write_bytes(wav); done += 1
        with wave.open(str(OUT / f'{i}.wav')) as w: secs = w.getnframes() / w.getframerate()
        log(f'made {i} {secs:.2f}s ({l["text"]!r}, {voice})')
        if n < len(ids): time.sleep(PACE)
    return done, failed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', nargs='?', default='all')
    ap.add_argument('ids', nargs='*')
    ap.add_argument('--voice', default=None)
    ap.add_argument('--model', default='gemini-3.8-flash-tts')
    a = ap.parse_args()
    if a.cmd == 'check':
        print('GEMINI_API_KEY is set.' if os.environ.get('GEMINI_API_KEY') else 'GEMINI_API_KEY is NOT set.'); return
    voice = a.voice or used_voice() or DATA['voice']
    if used_voice() and voice != used_voice():
        print(f'Switching voice from {used_voice()} to {voice}: the old clips go to voices/_old.')
        set_aside(LINES)
    if a.cmd == 'redo':
        bad = [i for i in a.ids if i not in LINES]
        if bad: sys.exit('Not in the list: ' + ', '.join(bad))
        set_aside(a.ids); ids = a.ids
    elif a.cmd == 'all':
        ids = [i for i in LINES if not (OUT / f'{i}.wav').exists()]
    else:
        sys.exit(__doc__)
    key()
    if not ids: print('Every clip is already made.')
    else:
        print(f'Making {len(ids)} clip(s) in the voice {voice}. About {len(ids) * (PACE + 2) / 60:.0f} minutes; leave this window open.')
        log(f'start: {len(ids)} clips, voice {voice}, model {a.model}')
        done, failed = make(a.model, voice, ids)
        print(f'\nMade {done}.' + (f' {failed} could not be made; run this again to retry them.' if failed else ''))
        log(f'end: made {done}, failed {failed}')
    write_page(voice)
    print('Wrote listen.html. Tell Claude when it is done, and Claude will put the clips in the games.')

if __name__ == '__main__':
    main()
