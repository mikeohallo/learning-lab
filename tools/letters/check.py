"""Draw each letter with its tracing path: grey letter, numbered start dots, arrows along each stroke."""
import json, math, sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from glyphs import *
from strokes import W, build, skeleton

COL = [(236, 60, 140), (40, 130, 230), (250, 150, 20)]
F = ImageFont.truetype('/home/claude/fonts/Nunito.ttf', 26)
FB = ImageFont.truetype('/home/claude/fonts/Fredoka.ttf', 30)

def tile(ch, data, s=0.42, show_skel=False):
    m, to_px, to_font, _ = mask(ch, s)
    h, w = m.shape
    im = Image.new('RGB', (w, h), 'white'); d = ImageDraw.Draw(im)
    for y, c, dash in ((ASC, (150, 150, 150), True), (XH, (90, 90, 90), False), (0, (90, 90, 90), False), (DESC, (150, 150, 150), True)):
        py = to_px(0, y)[1]
        if dash:
            for x in range(0, w, 14): d.line([(x, py), (x + 7, py)], fill=c, width=2)
        else: d.line([(0, py), (w, py)], fill=c, width=2)
    rgb = np.asarray(im).copy(); rgb[m] = (220, 220, 228); im = Image.fromarray(rgb); d = ImageDraw.Draw(im)
    if show_skel:
        sk = skeletonize_scaled(ch, s)
    for k, st in enumerate(data['strokes']):
        c = COL[k % 3]
        if 'dot' in st:
            x, y = to_px(*st['dot']); r = 13
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
            d.text((x + 16, y - 18), str(k + 1), fill=c, font=FB); continue
        P = [to_px(*p) for p in st['pts']]
        d.line(P, fill=c, width=5, joint='curve')
        # arrows every ~70 px of path
        acc, nxt = 0, 45
        for (x0, y0), (x1, y1) in zip(P, P[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            while L and acc + L >= nxt:
                t = (nxt - acc) / L; ax, ay = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                ang = math.atan2(y1 - y0, x1 - x0)
                pts = [(ax + 13 * math.cos(ang), ay + 13 * math.sin(ang)),
                       (ax + 9 * math.cos(ang + 2.5), ay + 9 * math.sin(ang + 2.5)),
                       (ax + 9 * math.cos(ang - 2.5), ay + 9 * math.sin(ang - 2.5))]
                d.polygon(pts, fill=c); nxt += 70
            acc += L
        x, y = P[0]; r = 12
        d.ellipse([x - r, y - r, x + r, y + r], fill=(40, 170, 80), outline='white', width=3)
        d.text((x + 14, y - 34), str(k + 1), fill=c, font=FB)
    d.text((8, 4), ch, fill=(58, 40, 82), font=FB)
    return im

def sheet(chars, out, cols=7):
    data = json.loads((HERE / 'letters.json').read_text())['letters']
    tiles = [tile(ch, data[ch]) for ch in chars]
    th = max(t.height for t in tiles); rows = math.ceil(len(tiles) / cols)
    cw = max(t.width for t in tiles)
    sh = Image.new('RGB', (cols * (cw + 16) + 16, rows * (th + 16) + 16), (240, 238, 245))
    for i, t in enumerate(tiles):
        sh.paste(t, (16 + (i % cols) * (cw + 16) + (cw - t.width) // 2, 16 + (i // cols) * (th + 16)))
    sh.save(out); return sh.size

if __name__ == '__main__':
    print(sheet(sys.argv[1] if len(sys.argv) > 1 else 'abcdefghijklmnopqrstuvwxyz', 'work/check.png'))
