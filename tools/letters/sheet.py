"""One page showing how every letter is formed in the game, for checking against the school's chart."""
import json
from PIL import Image, ImageDraw, ImageFont
from check import tile
from glyphs import HERE
data = json.loads((HERE / 'letters.json').read_text())['letters']
tiles = [tile(ch, data[ch], s=0.40) for ch in 'abcdefghijklmnopqrstuvwxyz']
cols, gap = 7, 26
cw = max(t.width for t in tiles); th = max(t.height for t in tiles)
W = cols * cw + (cols + 1) * gap
top = 230; rows = 4
H = top + rows * (th + gap) + 150
sh = Image.new('RGB', (W, H), (255, 248, 236)); d = ImageDraw.Draw(sh)
T = ImageFont.truetype('/home/claude/fonts/Fredoka.ttf', 64); B = ImageFont.truetype('/home/claude/fonts/Nunito.ttf', 34)
d.text((gap, 40), 'Letters game: how each letter is formed', fill=(58, 40, 82), font=T)
d.text((gap, 130), 'Green dot = where to start. Numbers = stroke order. Arrows = direction. The letters are NSW Foundation Style (Edu NSW ACT Foundation font).', fill=(110, 92, 134), font=B)
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    x = gap + c * (cw + gap) + (cw - t.width) // 2; y = top + r * (th + gap)
    sh.paste(t, (x, y))
d.text((gap, H - 110), 'Please check each one against the school\'s NSW Foundation chart, especially e, f, k, q, s, w and y.', fill=(58, 40, 82), font=B)
sh.save(HERE / 'work' / 'Letter_shapes_check.jpg', quality=90); print(sh.size)
