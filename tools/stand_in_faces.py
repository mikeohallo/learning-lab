"""Make plain stand-in pictures for the 30 monster faces, so the tests and screenshot checks can run without the
Monster Book's artwork (which stays out of this repo). Each stand-in is a flat coloured circle with its number.

    python3 tools/stand_in_faces.py [SITE_DIR]     writes SITE_DIR/faces/F01.webp ... F30.webp (default: the repo root)

It never overwrites a real face: if a picture is already there, it's left alone."""
import colorsys, sys
from pathlib import Path
from PIL import Image, ImageDraw

site = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
faces = site / 'faces'
faces.mkdir(exist_ok=True)
made = 0
for i in range(1, 31):
    f = faces / f'F{i:02d}.webp'
    if f.exists():
        continue
    r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb((i * 0.618) % 1, .45, .9))
    im = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((16, 16, 240, 240), fill=(r, g, b, 255), outline=(60, 40, 80, 255), width=8)
    d.text((128, 128), str(i), fill=(60, 40, 80, 255), anchor='mm', font_size=96)
    im.save(f, 'WEBP', quality=90)
    made += 1
print(f'{made} stand-in faces made in {faces}')
