"""Build the tracing paths for a-z from the NSW Foundation glyphs.

Each letter is written as strokes of rough waypoints in font units (y up), in the order and direction
NSW Foundation Style teaches. Each stroke is snapped onto the glyph's centre line (skeleton) and followed
along it, so the path matches the letter exactly. A stroke of one point is a dot (i, j).
    python3 strokes.py            -> letters.json and work/check_*.png
"""
import json, heapq, math, sys
from pathlib import Path
import numpy as np
from skimage.morphology import skeletonize
from glyphs import *

W = {
 'a': [[(245,402),(120,402),(45,240),(60,60),(130,25),(225,200),(272,402),(245,18)]],
 'b': [[(118,768),(28,18),(68,190),(160,385),(225,408),(318,290),(255,70),(170,22),(45,22)]],
 'c': [[(328,382),(210,410),(70,340),(38,140),(140,12),(300,178)]],
 'd': [[(245,402),(120,402),(45,240),(60,60),(130,25),(235,200),(328,768),(272,18)]],
 'e': [[(42,172),(190,250),(300,345),(215,408),(85,365),(35,195),(70,35),(170,12),(290,128)]],
 'f': [[(300,762),(225,790),(160,745),(118,520),(80,18)], [(15,395),(190,395)]],
 'g': [[(290,404),(165,404),(75,290),(75,75),(150,50),(290,240),(330,404),(300,-40),(262,-290),(150,-350),(-25,-308)]],
 'h': [[(125,768),(25,18),(60,190),(150,375),(230,410),(292,300),(262,18)]],
 'i': [[(95,400),(60,18)], [(95,578)]],
 'j': [[(100,400),(62,-200),(-40,-340),(-240,-312)], [(100,578)]],
 'k': [[(108,768),(28,18),(68,200),(178,408),(275,335),(190,252),(92,208),(252,18)]],
 'l': [[(125,768),(40,18)]],
 'm': [[(95,400),(48,18),(75,225),(185,408),(265,345),(245,18),(262,230),(380,408),(458,335),(440,18)]],
 'n': [[(95,400),(48,18),(72,225),(188,408),(270,340),(255,18)]],
 'o': [[(235,410),(110,365),(30,150),(95,12),(230,110),(300,330),(235,410)]],
 'p': [[(95,400),(28,-330),(70,190),(190,410),(310,300),(232,72),(150,40),(55,40)]],
 'q': [[(285,404),(155,404),(65,290),(60,70),(130,35),(270,245),(330,404),(292,-40),(278,-300),(330,-340),(400,-232)]],
 'r': [[(95,400),(45,18),(70,225),(182,405),(262,392),(300,322)]],
 's': [[(292,350),(205,410),(85,382),(68,300),(200,222),(300,135),(250,22),(120,14),(22,82)]],
 't': [[(165,768),(110,18)], [(10,410),(300,410)]],
 'u': [[(82,400),(42,120),(100,15),(200,65),(268,220),(310,400),(275,18)]],
 'v': [[(82,400),(45,110),(100,15),(225,125),(352,400)]],
 'w': [[(80,400),(45,100),(110,15),(250,150),(290,240),(310,400),(300,200),(350,15),(450,100),(550,400)]],
 'x': [[(15,396),(272,18)], [(332,396),(-22,18)]],
 'y': [[(88,400),(48,120),(118,28),(240,100),(320,240),(350,400),(320,0),(290,-250),(200,-345),(20,-302)]],
 'z': [[(60,400),(330,400),(22,18),(300,18)]],
}

S = 1.0          # px per font unit for the skeleton

def skeleton(ch):
    m, to_px, to_font, _ = mask(ch, S)
    sk = skeletonize(m)
    return m, sk, to_px, to_font

def snap(sk, px, py):
    ys, xs = np.nonzero(sk)
    d = (xs - px) ** 2 + (ys - py) ** 2
    i = int(np.argmin(d)); return (int(ys[i]), int(xs[i])), math.sqrt(d[i])

def path_on(sk, a, b):
    """Shortest 8-connected path along the skeleton from a to b (row, col)."""
    H, Wd = sk.shape
    dist = {a: 0.0}; prev = {}; pq = [(0.0, a)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == b: break
        if d > dist.get(u, 1e18): continue
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if not dy and not dx: continue
                v = (u[0] + dy, u[1] + dx)
                if 0 <= v[0] < H and 0 <= v[1] < Wd and sk[v]:
                    nd = d + (1.4142 if dy and dx else 1.0)
                    if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    if b not in dist: return None
    out = [b]
    while out[-1] != a: out.append(prev[out[-1]])
    return out[::-1]

def rdp(pts, eps):
    if len(pts) < 3: return pts
    a, b = np.array(pts[0]), np.array(pts[-1]); ab = b - a; L = np.hypot(*ab)
    ds = [abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / L if L else float(np.hypot(p[0] - a[0], p[1] - a[1])) for p in pts[1:-1]]
    i = int(np.argmax(ds)) + 1
    if ds[i - 1] > eps: return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]

def smooth(seg, sigma=9.0):
    """Gaussian-smooth one section along its length, keeping both ends where they are
    (the ends are the waypoints, including the sharp turns where a stroke goes back up a line)."""
    P = np.array(seg, float)
    if len(P) < 5: return [tuple(p) for p in P]
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    t = np.arange(0, d[-1], 2.0); t = np.r_[t, d[-1]] if t[-1] < d[-1] else t
    R = np.c_[np.interp(t, d, P[:, 0]), np.interp(t, d, P[:, 1])]
    k = int(sigma); w = np.exp(-0.5 * (np.arange(-3 * k, 3 * k + 1) / sigma) ** 2); w /= w.sum()
    pad = np.r_[np.repeat(R[:1], 3 * k, 0), R, np.repeat(R[-1:], 3 * k, 0)]
    S = np.c_[np.convolve(pad[:, 0], w, 'valid'), np.convolve(pad[:, 1], w, 'valid')]
    # pull the smoothed line back onto the exact ends, fading out over a short distance
    n = len(S); f = np.clip(np.minimum(np.arange(n), np.arange(n)[::-1]) / (2 * k), 0, 1)[:, None]
    S = R * (1 - f) + S * f
    return [tuple(p) for p in S]

def build(ch, wps):
    m, sk, to_px, to_font = skeleton(ch)
    strokes, worst = [], 0
    for stroke in wps:
        if len(stroke) == 1:                       # a dot: centre of the dot blob
            x, y = stroke[0]; strokes.append({'dot': [round(x), round(y)]}); continue
        snapped = []
        for (x, y) in stroke:
            (r, c), d = snap(sk, *to_px(x, y)); worst = max(worst, d); snapped.append((r, c))
        if len(snapped) == 2:                      # a straight stroke: l, i, t, the bars of f and t, x
            pts = [to_font(c + .5, r + .5) for r, c in snapped]
            strokes.append({'pts': [[round(x), round(y)] for x, y in pts]}); continue
        pts = []
        for a, b in zip(snapped, snapped[1:]):
            seg = path_on(sk, a, b)
            if seg is None: raise SystemExit(f'{ch}: no skeleton path between waypoints')
            seg = smooth([to_font(c + .5, r + .5) for r, c in seg])
            pts += seg if not pts else seg[1:]
        pts = rdp([(round(x, 1), round(y, 1)) for x, y in pts], 2.0)
        strokes.append({'pts': [[round(x), round(y)] for x, y in pts]})
    _, (x0, y0, x1, y1), w = glyph(ch)
    return {'strokes': strokes, 'advance': w, 'bbox': [round(x0), round(y0), round(x1), round(y1)]}, worst

if __name__ == '__main__':
    only = sys.argv[1:] or list(W)
    out = {}
    for ch in only:
        out[ch], worst = build(ch, W[ch])
        print(f'{ch}: {len(out[ch]["strokes"])} stroke(s), farthest waypoint {worst:.0f} units from the centre line')
    if not sys.argv[1:]:
        meta = {'font': 'Edu NSW ACT Foundation (OFL), AU School Handwriting Fonts Project', 'xHeight': XH, 'ascender': ASC, 'descender': DESC}
        (HERE / 'letters.json').write_text(json.dumps({'meta': meta, 'letters': out}, separators=(',', ':')))
