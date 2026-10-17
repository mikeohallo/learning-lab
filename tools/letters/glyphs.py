"""Shared helpers: the NSW Foundation glyphs (Edu NSW ACT Foundation, OFL) as filled masks in font units."""
from pathlib import Path
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
FONT = TTFont(HERE / 'fonts' / 'EduNSWACTFoundation-400.ttf')
GS, CMAP = FONT.getGlyphSet(), FONT.getBestCmap()
XH, ASC, DESC = 416, 772, -356          # x-height, tall-letter top, tail bottom (font units, y up)
TOP, BOT = 820, -400                    # frame drawn for every letter

def glyph(ch):
    g = GS[CMAP[ord(ch)]]
    bp = BoundsPen(GS); g.draw(bp)
    return g, bp.bounds, g.width

def svg_path(ch):
    g, _, _ = glyph(ch); p = SVGPathPen(GS); g.draw(p); return p.getCommands()

def mask(ch, s=1.0, pad=60):
    """Filled glyph rasterised at s px per font unit. Returns (array, to_px, to_font)."""
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.basePen import BasePen
    g, (x0, y0, x1, y1), w = glyph(ch)
    X0, X1 = min(x0, 0) - pad, max(x1, w) + pad
    W, H = int((X1 - X0) * s), int((TOP - BOT) * s)
    to_px = lambda x, y: ((x - X0) * s, (TOP - y) * s)
    to_font = lambda px, py: (px / s + X0, TOP - py / s)
    # flatten contours into polygons
    class Flat(BasePen):
        def __init__(self, gs): super().__init__(gs); self.polys = []; self.cur = []
        def _moveTo(self, p): self.cur = [p]
        def _lineTo(self, p): self.cur.append(p)
        def _curveToOne(self, p1, p2, p3):
            p0 = self.cur[-1]
            for t in np.linspace(0, 1, 24)[1:]:
                mt = 1 - t
                self.cur.append((mt**3*p0[0]+3*mt*mt*t*p1[0]+3*mt*t*t*p2[0]+t**3*p3[0], mt**3*p0[1]+3*mt*mt*t*p1[1]+3*mt*t*t*p2[1]+t**3*p3[1]))
        def _qCurveToOne(self, p1, p2):
            p0 = self.cur[-1]
            for t in np.linspace(0, 1, 16)[1:]:
                mt = 1 - t
                self.cur.append((mt*mt*p0[0]+2*mt*t*p1[0]+t*t*p2[0], mt*mt*p0[1]+2*mt*t*p1[1]+t*t*p2[1]))
        def _closePath(self): self.polys.append(self.cur); self.cur = []
        def _endPath(self): self.polys.append(self.cur); self.cur = []
    pen = Flat(GS); g.draw(pen)
    # even-odd fill handles counters (holes)
    im = Image.new('L', (W, H), 0)
    acc = np.zeros((H, W), bool)
    for poly in pen.polys:
        if len(poly) < 3: continue
        m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([to_px(*p) for p in poly], fill=1)
        acc ^= np.asarray(m, bool)
    return acc, to_px, to_font, (X0, X1)
