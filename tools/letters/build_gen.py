import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
pics = json.loads((HERE / 'letters_data.json').read_text(encoding='utf-8'))['newPictures']
src = (HERE / 'letters_gen_src.py').read_text(encoding='utf-8')
out = src.replace("PICTURES = {}   # filled in by the build step: name -> what it shows",
                  'PICTURES = {\n' + ''.join(f'    {k!r}: {v!r},\n' for k, v in pics.items()) + '}')
(HERE / 'letters_gen.py').write_text(out, encoding='utf-8'); print('letters_gen.py,', len(pics), 'pictures')
