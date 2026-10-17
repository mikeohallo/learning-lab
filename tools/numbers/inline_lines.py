"""Put the narrator's lines (number_lines.json) into the page, so it can show or say them before any clips exist.

    python3 numbers/inline_lines.py"""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
page = HERE.parent / 'site' / 'app.html'
lines = json.loads((HERE / 'number_lines.json').read_text(encoding='utf-8'))['lines']
js = json.dumps({l['id']: l['text'] for l in lines}, ensure_ascii=False, separators=(',', ':'))
s = page.read_text(encoding='utf-8')
s, n = re.subn(r'/\*NUM_LINES\*/.*?/\*/NUM_LINES\*/', lambda m: '/*NUM_LINES*/' + js + '/*/NUM_LINES*/', s, flags=re.S)
assert n == 1
page.write_text(s, encoding='utf-8')
print(f'put {len(lines)} lines into {page.name}')
