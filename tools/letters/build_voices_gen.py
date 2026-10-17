"""Bakes the clip list from letters_data.json into voices_gen.py, so it runs on its own in the laptop's letters folder."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
import wordlist
d = wordlist.load()
def block(name, items, note):
    return f'{name} = {{\n' + ''.join(f'    {k!r}: {v!r},\n' for k, v in items.items()) + '}'
src = (HERE / 'voices_gen_src.py').read_text(encoding='utf-8')
for name, items in [('LETTER_NAMES', {k: v['name'] for k, v in d['letters'].items()}),
                    ('LETTER_TIPS', {k: v['tip'] for k, v in d['letters'].items()}),
                    ('WORDS', {k: v['text'] for k, v in d['words'].items()}),
                    ('PROMPTS', d['prompts'])]:
    line = next(l for l in src.splitlines() if l.startswith(name + ' = {}'))
    src = src.replace(line, block(name, items, ''))
(HERE / 'voices_gen.py').write_text(src, encoding='utf-8')
n = 2 * len(d['letters']) + len(d['words']) + len(d['prompts'])
print('voices_gen.py,', n, 'clips per voice')
