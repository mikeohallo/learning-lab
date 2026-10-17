import json
from pathlib import Path
import wordlist
HERE = Path(__file__).resolve().parent
clips = wordlist.load()['clips']
src = (HERE / 'recorder_src.html').read_text(encoding='utf-8')
out = src.replace('/*CLIPS*/[]', json.dumps(clips, ensure_ascii=False))
(HERE / 'recorder.html').write_text(out, encoding='utf-8'); print('recorder.html', len(out), 'bytes,', len(clips), 'clips')
