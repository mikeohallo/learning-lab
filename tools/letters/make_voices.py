"""Turn the voice clips (recorded with recorder.html, or made by voices_gen.py) into the site's voice files.

    python3 make_voices.py IN_DIR [OUT_DIR]     IN_DIR holds mum/ and dad/ folders of .webm or .wav clips

For each clip: decode, find where the speech is (ignoring the first 250 ms and last 200 ms, where key presses
land), keep the speech with a little air either side, take out rumble below 70 Hz, even out the level, short
fades, mono MP3. Letter sounds and names keep only their strongest take, so a clip with a few tries or a cough still gives
one clean sound; words and sayings keep everything from the first sound to the last.
Writes OUT_DIR/<voice>/<id>.mp3 and OUT_DIR/index.json (default OUT_DIR: ../site/letters/voices), a listening
page with copies of the clips in work/voice_check/review.html, and reports clips worth checking."""
import json, shutil, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
import wordlist
CLIPS = {c['id']: c for c in wordlist.load()['clips']}
SR = 44100
FR = 441                      # 10 ms frames

def decode(p):
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(p), '-ac', '1', '-ar', str(SR),
                        '-af', 'highpass=f=70', '-f', 's16le', '-'], capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode()[:120])
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float64) / 32768

def segments(x):
    """Stretches of speech as (start frame, end frame), gaps under 250 ms bridged."""
    n = len(x) // FR
    if n < 5: return [], None
    e = np.array([10 * np.log10(np.mean(x[i * FR:(i + 1) * FR] ** 2) + 1e-12) for i in range(n)])
    lo, hi = 25, max(25, n - 20)                       # skip the first 250 ms and the last 200 ms
    core = e[lo:hi]
    if not len(core): return [], e
    floor, peak = np.percentile(core, 10), core.max()
    act = np.zeros(n, bool); act[lo:hi] = e[lo:hi] > max(floor + 12, peak - 35)
    segs, i = [], lo
    while i < hi:
        if act[i]:
            j = i
            while j < hi and (act[j] or act[j:j + 25].any()): j += 1
            segs.append((i, j)); i = j
        else: i += 1
    return segs, e

def energy(x, a, b):
    return float(np.sum(x[a * FR:b * FR] ** 2))

def pick(x, kind):
    segs, e = segments(x)
    segs = [s for s in segs if s[1] - s[0] >= 3]       # drop blips under 30 ms
    if not segs: return None, 0
    if kind in ('sound', 'name'):                      # one short thing: the strongest single take
        a, b = max(segs, key=lambda s: energy(x, *s)); extra = 0
    else:                                              # first to last, without faint stragglers
        top = max(energy(x, *s) / (s[1] - s[0]) for s in segs)
        keep = [s for s in segs if energy(x, *s) / (s[1] - s[0]) > top * 10 ** (-2.0)]
        a, b = keep[0][0], keep[-1][1]; extra = len(segs) - len(keep)
    a = max(0, a - 3); b = min(len(x) // FR, b + 6)     # 30 ms before, 60 ms after
    return x[a * FR:b * FR].copy(), len(segs) - 1 + extra

def level(y):
    rms = 10 * np.log10(np.mean(y ** 2) + 1e-12); pk = 20 * np.log10(np.abs(y).max() + 1e-12)
    g = min(-20 - rms, -1.5 - pk)                      # aim for -20 dBFS RMS, never past -1.5 dBFS peak
    y = y * 10 ** (g / 20)
    fi, fo = int(SR * 0.008), int(SR * 0.025)
    y[:fi] *= np.linspace(0, 1, fi); y[-fo:] *= np.linspace(1, 0, fo)
    return y, rms, g

def encode(y, out):
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-',
                        '-b:a', '64k', str(out)], input=pcm, capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode()[:120])

PAGE = """<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><title>Letters voices: check</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{font:16px/1.45 system-ui,sans-serif;margin:24px auto;max-width:900px;padding:0 16px;color:#222;background:#fffaf2}
h1{font-size:24px} h2{font-size:18px;margin-top:26px} .grid{display:flex;flex-wrap:wrap;gap:8px}
button{font:inherit;padding:8px 12px;border-radius:10px;border:1px solid #c9b79a;background:#fff;cursor:pointer;min-width:64px}
button.on{background:#ffd98a} .flag{border-color:#d05;color:#a03}
</style></head><body><h1>Letters voices, as the game will play them</h1>
<p>Each button plays one processed clip. Red ones are worth a listen first (several takes, very short or very long).</p>
%BODY%<script>let a=null,b=null;document.querySelectorAll('button[data-src]').forEach(x=>x.onclick=()=>{
if(a){a.pause();b.classList.remove('on')}a=new Audio(x.dataset.src);b=x;x.classList.add('on');
a.onended=()=>x.classList.remove('on');a.play()});</script></body></html>"""

def main(src, out=None):
    src = Path(src); out = Path(out) if out else HERE.parent / 'site' / 'letters' / 'voices'
    index, report, page = {}, [], ''
    for v in ('mum', 'dad'):
        files = sorted(p for p in (src / v).iterdir() if p.suffix in ('.webm', '.wav')) if (src / v).exists() else []
        (out / v).mkdir(parents=True, exist_ok=True); done = []
        groups = {'sound': [], 'name': [], 'word': [], 'prompt': [], 'praise': []}
        for f in files:
            c = CLIPS.get(f.stem)
            if not c: report.append(f'{v}/{f.name}: not in the clip list, skipped'); continue
            try:
                seg, others = pick(decode(f), c['kind'])
            except RuntimeError as err:
                report.append(f'{v}/{f.stem}: could not read ({err})'); continue
            if seg is None or len(seg) < SR * 0.04:
                report.append(f'{v}/{f.stem}: nothing heard'); continue
            y, rms, g = level(seg)
            encode(y, out / v / f'{f.stem}.mp3')
            d = len(y) / SR; notes = []
            if others and c['kind'] in ('sound', 'name'): notes.append(f'{others + 1} takes or noises, kept the strongest')
            if c['kind'] == 'sound' and d > 1.6: notes.append(f'long ({d:.1f} s)')
            if c['kind'] != 'sound' and d > 3.5: notes.append(f'long ({d:.1f} s)')
            if g > 24: notes.append(f'very quiet, boosted {g:.0f} dB')
            if notes: report.append(f'{v}/{f.stem}: ' + '; '.join(notes))
            done.append(f.stem)
            groups[c['kind']].append((f.stem, d, bool(notes)))
        index[v] = sorted(done)
        if done:
            page += f'<h2>{"Mum" if v == "mum" else "Dad"} ({len(done)})</h2>'
            for kind, items in groups.items():
                if items:
                    page += '<div class="grid">' + ''.join(
                        f'<button data-src="{v}/{i}.mp3" class="{"flag" if fl else ""}" title="{d:.2f} s">{i.split("_", 1)[1]}</button>'
                        for i, d, fl in items) + '</div><p></p>'
        missing = [k for k in CLIPS if k not in done]
        print(f'{v}: {len(done)} clips' + (f' ({len(missing)} of the {len(CLIPS)} not recorded in this voice)' if missing else ''))
    (out / 'index.json').write_text(json.dumps(index, separators=(',', ':')))
    review = HERE / 'work' / 'voice_check'           # a listening page with its own copies (not part of the site)
    if review.exists(): shutil.rmtree(review)
    for v in ('mum', 'dad'): shutil.copytree(out / v, review / v)
    (review / 'review.html').write_text(PAGE.replace('%BODY%', page), encoding='utf-8')
    both = set(index['mum']) | set(index['dad'])
    gaps = [k for k in CLIPS if k not in both]
    print('covered by one voice or the other:', len(both), 'of', len(CLIPS), ('; missing: ' + ', '.join(gaps)) if gaps else '')
    for r in report: print('   check:', r)
    print('wrote', out)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
