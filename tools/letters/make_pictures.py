"""Turn the AI Studio pictures into the game's pictures.
    python3 make_pictures.py IN_DIR [--picks hat=2,kite=1]
IN_DIR is the laptop's letters/pictures. For each picture name the newest version is used (or the one picked).
The white background is made transparent (only white connected to the edges, so white inside the picture stays),
the picture is trimmed, centred on a square and saved as site/letters/pics/<name>.webp at 360 px.
Also writes work/pictures_sheet.jpg to look over."""
import argparse, json, re
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'site' / 'letters' / 'pics'
NAMES = list(json.loads((HERE / 'letters_data.json').read_text(encoding='utf-8'))['newPictures'])

def cut(im, white=232):
    rgb = np.asarray(im.convert('RGB')).astype(int)
    near = (rgb.min(axis=2) >= white) & ((rgb.max(axis=2) - rgb.min(axis=2)) < 18)
    lab, _ = ndimage.label(near)
    edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    bg = np.isin(lab, list(edge))
    bg = ndimage.binary_opening(bg, iterations=1)
    alpha = Image.fromarray(np.where(bg, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    out = im.convert('RGBA'); out.putalpha(alpha)
    a = np.asarray(alpha) > 24
    ys, xs = np.nonzero(a)
    if not len(xs): return out, 0.0
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    return out.crop(box), a.mean()

def square(im, size=360, margin=.06):
    s = max(im.size); pad = int(s * margin); c = Image.new('RGBA', (s + 2 * pad, s + 2 * pad), (0, 0, 0, 0))
    c.paste(im, (pad + (s - im.width) // 2, pad + (s - im.height) // 2), im)
    return c.resize((size, size), Image.LANCZOS)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('--picks', default=''); ap.add_argument('--out', default='')
    a = ap.parse_args(); picks = dict(p.split('=') for p in a.picks.split(',') if p)
    global OUT
    if a.out: OUT = Path(a.out)
    OUT.mkdir(parents=True, exist_ok=True); tiles = []
    for n in NAMES:
        vs = {int(m.group(1)): f for f in Path(a.src).glob(f'{n}_v*.*') if (m := re.search(r'_v(\d+)$', f.stem))}
        if not vs: print(f'{n}: not made yet'); continue
        v = int(picks.get(n, max(vs)))
        pic, fill = cut(Image.open(vs[v]))
        sq = square(pic); sq.save(OUT / f'{n}.webp', quality=86, method=6)
        note = '' if .03 < fill < .75 else '   <- check: background removal looks off'
        print(f'{n}: v{v} of {len(vs)}{note}'); tiles.append((n, v, sq))
    if tiles:
        F = ImageFont.truetype('/home/claude/fonts/Nunito.ttf', 22)
        cols = 7; rows = (len(tiles) + cols - 1) // cols
        sh = Image.new('RGB', (cols * 200, rows * 230), (255, 248, 236)); d = ImageDraw.Draw(sh)
        for i, (n, v, sq) in enumerate(tiles):
            x, y = (i % cols) * 200, (i // cols) * 230
            t = sq.resize((180, 180)); sh.paste(t, (x + 10, y + 10), t); d.text((x + 12, y + 196), f'{n} v{v}', fill=(58, 40, 82), font=F)
        (HERE / 'work').mkdir(exist_ok=True); sh.save(HERE / 'work' / 'pictures_sheet.jpg', quality=88)
        print('sheet: work/pictures_sheet.jpg')

if __name__ == '__main__':
    main()
