"""Turn the narrator's clips (from number_voices.py) into the site's voice files.

    python3 make_number_voices.py IN_DIR [OUT_DIR]    IN_DIR holds the .wav clips (numbers/voices/narrator on the laptop)

For each clip: trim the silence either side (keeping a little air), take out rumble below 70 Hz, even out the
level (-20 dBFS RMS, never past -1.5 dBFS peak), short fades, mono MP3. Writes OUT_DIR/<id>.mp3 and
OUT_DIR/index.json (default OUT_DIR: ../site/numbers/voices), and reports clips worth a listen."""
import json, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
LINES = {l['id']: l for l in json.loads((HERE / 'number_lines.json').read_text(encoding='utf-8'))['lines']}
SR, FR = 44100, 441                                    # 10 ms frames

def decode(p):
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(p), '-ac', '1', '-ar', str(SR), '-af', 'highpass=f=70',
                        '-f', 's16le', '-'], capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode()[:120])
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float64) / 32768

def trim(x):
    """From the first sound to the last, with 40 ms before and 80 ms after. Text-to-speech has no key presses
    to skip, so unlike the recorded voices nothing at the ends is ignored."""
    n = len(x) // FR
    if n < 3: return None
    e = np.array([10 * np.log10(np.mean(x[i * FR:(i + 1) * FR] ** 2) + 1e-12) for i in range(n)])
    on = np.where(e > max(min(np.percentile(e, 10) + 12, e.max() - 6), e.max() - 40))[0]   # a clip with no silence keeps it all
    if not len(on): return None
    a, b = max(0, on[0] - 4), min(n, on[-1] + 9)
    return x[a * FR:b * FR].copy()

def level(y):
    rms = 10 * np.log10(np.mean(y ** 2) + 1e-12); pk = 20 * np.log10(np.abs(y).max() + 1e-12)
    g = min(-20 - rms, -1.5 - pk)
    y = y * 10 ** (g / 20)
    fi, fo = int(SR * .008), int(SR * .025)
    y[:fi] *= np.linspace(0, 1, fi); y[-fo:] *= np.linspace(1, 0, fo)
    return y, g

def encode(y, out):
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-', '-b:a', '64k', str(out)],
                       input=pcm, capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode()[:120])

def main(src, out=None):
    src = Path(src); out = Path(out) if out else HERE.parent / 'site' / 'numbers' / 'voices'
    out.mkdir(parents=True, exist_ok=True)
    done, notes = [], []
    for f in sorted(src.glob('*.wav')):
        if f.stem not in LINES: notes.append(f'{f.name}: not in the line list, skipped'); continue
        y = trim(decode(f))
        if y is None or len(y) < SR * .1: notes.append(f'{f.stem}: nothing heard'); continue
        y, g = level(y); encode(y, out / f'{f.stem}.mp3'); done.append(f.stem)
        d = len(y) / SR, LINES[f.stem]
        if d[1]['kind'] == 'number' and d[0] > 1.4: notes.append(f'{f.stem}: long for one number ({d[0]:.1f} s)')
        if d[1]['kind'] != 'number' and d[0] > 3.5: notes.append(f'{f.stem}: long ({d[0]:.1f} s)')
        if g > 24: notes.append(f'{f.stem}: very quiet, boosted {g:.0f} dB')
    (out / 'index.json').write_text(json.dumps({'clips': sorted(done)}, separators=(',', ':')))
    missing = [i for i in LINES if i not in done]
    print(f'{len(done)} of {len(LINES)} clips' + (f'; missing: {", ".join(missing)}' if missing else ''))
    for n in notes: print('   check:', n)
    print('wrote', out)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
