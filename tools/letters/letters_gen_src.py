"""Letters game picture maker: draws the word pictures (hat, kite, sun...) with Google AI Studio's image model,
in the Monster Book's style. Same setup as the monster kit maker.

    py letters_gen.py check            reference image, key and package present? (no API call)
    py letters_gen.py prompts hat      show a prompt (free)
    py letters_gen.py                  make every picture that hasn't been made yet -> pictures/<name>_v1.png
    py letters_gen.py hat kite         make (or remake) just those -> a new _vN each time
    py letters_gen.py all              remake everything
    py letters_gen.py remake           remake the names listed in remake.txt (what 'Remake pictures.bat' runs)

Options:
    --model gemini-3-pro-image      image model (default; gemini-nano-banana-2.1 is cheaper)
    --size 1K                       1K, 2K or 4K (default 1K: the game shows them small)

The API key is read from the GEMINI_API_KEY environment variable; google-genai must be installed
(py -m pip install --upgrade google-genai). Outputs are never overwritten.
"""
import argparse, base64, io, os, re, sys, time
from datetime import datetime
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / 'pictures'
REF = HERE.parent / 'monster_style_ref.png'
PICTURES = {}   # filled in by the build step: name -> what it shows

PROMPT = """Image 1 is a style reference only: pages from a children's monster book. Copy its art style exactly: bold dark outlines, bright saturated colours, soft painted shading with a little surface texture, friendly rounded cartoon shapes. Do not copy any monster, body part, star or sticker border from Image 1.

Draw ONE {what}, on its own, centred, filling about 70% of a square picture, on a plain pure white background. Make it simple and instantly recognisable to a young child, like a picture in an alphabet book.{person}

No text, letters or numbers anywhere. No sticker border, no frame, no stars, no ground line, no shadow underneath, and no other objects."""
PERSON = " Every person has exactly two arms and two legs, natural-length arms, and hands with the right number of fingers."

def prompt_for(name):
    what = PICTURES[name]
    return PROMPT.format(what=what, person=PERSON if name in ('queen',) else '')

def _client():
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        sys.exit('GEMINI_API_KEY is not set. Run:  setx GEMINI_API_KEY "your-key"  then open a new window.')
    try:
        from google import genai
    except ImportError:
        sys.exit('The google-genai package is missing. Run:  py -m pip install --upgrade google-genai')
    return genai.Client(api_key=key)

def ref_bytes(max_px=1536):
    im = Image.open(REF).convert('RGB')
    s = min(1.0, max_px / max(im.size))
    if s < 1: im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=92); return buf.getvalue()

def _generate_once(client, model, prompt, refs, size):
    errors = []
    if hasattr(client, 'interactions'):
        try:
            parts = [{'type': 'image', 'data': base64.b64encode(b).decode('ascii'), 'mime_type': 'image/jpeg'} for b in refs] + [{'type': 'text', 'text': prompt}]
            it = client.interactions.create(model=model, input=parts,
                response_format={'type': 'image', 'mime_type': 'image/png', 'aspect_ratio': '1:1', 'image_size': size})
            img = getattr(it, 'output_image', None)
            if img is not None and getattr(img, 'data', None):
                d = img.data; return base64.b64decode(d) if isinstance(d, str) else bytes(d)
            errors.append('interactions: no image returned ' + str(getattr(it, 'output_text', '') or '')[:200])
        except Exception as e:
            errors.append(f'interactions: {e}')
    try:
        from google.genai import types
        contents = [types.Part.from_bytes(data=b, mime_type='image/jpeg') for b in refs] + [prompt]
        resp = client.models.generate_content(model=model, contents=contents,
            config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio='1:1', image_size=size)))
        for part in resp.candidates[0].content.parts:
            inline = getattr(part, 'inline_data', None)
            if inline is not None and inline.data:
                d = inline.data; return base64.b64decode(d) if isinstance(d, str) else bytes(d)
        errors.append('generateContent: no image returned')
    except Exception as e:
        errors.append(f'generateContent: {e}')
    raise RuntimeError(' | '.join(errors))

def generate(client, model, name, size):
    fake = os.environ.get('GEN_FAKE')           # testing only: copy an existing image, no API call
    if fake: return Path(fake).read_bytes()
    refs = [ref_bytes()]
    for attempt in range(3):
        try:
            return _generate_once(client, model, prompt_for(name), refs, size)
        except RuntimeError as e:
            msg = str(e)
            if attempt < 2 and re.search(r'429|503|500|overload|unavailable|RESOURCE_EXHAUSTED', msg, re.I):
                print(f'    busy, waiting 30 s ({msg[:80]})'); time.sleep(30); continue
            raise

def made(name):
    return sorted(OUT.glob(f'{name}_v*.*'))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('targets', nargs='*')
    ap.add_argument('--model', default='gemini-3-pro-image')
    ap.add_argument('--size', default='1K', choices=['1K', '2K', '4K'])
    a = ap.parse_args()
    t = a.targets
    if t[:1] == ['remake']:                      # names listed in remake.txt (one per line), for the double-click remake file
        f = HERE / 'remake.txt'
        t = [n.strip() for n in f.read_text(encoding='utf-8').split() if n.strip()] if f.exists() else []
        if not t: sys.exit('remake.txt is empty: nothing to remake.')
        print('Remaking: ' + ', '.join(t))
    if t[:1] == ['check']:
        print(('ok      ' if REF.exists() else 'MISSING ') + str(REF))
        print('key:', 'set' if os.environ.get('GEMINI_API_KEY') else 'GEMINI_API_KEY not set in this window')
        try:
            import google.genai  # noqa: F401
            print('google-genai: installed')
        except ImportError:
            print('google-genai: MISSING  (py -m pip install --upgrade google-genai)')
        done = [n for n in PICTURES if made(n)]
        print(f'pictures made so far: {len(done)} of {len(PICTURES)}')
        return
    if t[:1] == ['prompts']:
        for n in t[1:] or list(PICTURES): print(f'\n===== {n} =====\n{prompt_for(n)}')
        return
    unknown = [n for n in t if n != 'all' and n not in PICTURES]
    if unknown: sys.exit(f'Unknown picture(s): {", ".join(unknown)}. Known: {", ".join(PICTURES)}')
    names = list(PICTURES) if t == ['all'] else t or [n for n in PICTURES if not made(n)]
    if not names: print('Every picture has been made. Name one to remake it, e.g.  py letters_gen.py kite'); return
    if not REF.exists(): sys.exit(f'Missing the style reference: {REF}')
    client = None if os.environ.get('GEN_FAKE') else _client()
    OUT.mkdir(exist_ok=True)
    log = HERE / 'gen_log.csv'; ok = 0
    print(f'Making {len(names)} picture(s) with {a.model} at {a.size}.')
    for n in names:
        try:
            data = generate(client, a.model, n, a.size)
        except Exception as e:
            print(f'  {n}: failed: {e}'); continue
        v = max([int(p.stem.rsplit("_v", 1)[1]) for p in made(n) if p.stem.rsplit("_v", 1)[1].isdigit()], default=0) + 1
        path = OUT / f'{n}_v{v}{".jpg" if data[:3] == bytes([255, 216, 255]) else ".png"}'
        path.write_bytes(data)
        im = Image.open(path)
        print(f'  {n}: saved pictures/{path.name}  {im.width} x {im.height}')
        with log.open('a', encoding='utf-8') as f:
            f.write(f'{datetime.now().isoformat(timespec="seconds")},{n},{path.name},{a.model},{a.size}\n')
        ok += 1
    print(f'\n{ok} of {len(names)} made. Tell Claude when they are in.')

if __name__ == '__main__':
    main()
