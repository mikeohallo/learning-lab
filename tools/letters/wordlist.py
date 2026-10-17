"""The Letters word list as the tools need it: everyone's words (letters_data.json) plus the private family words
(letters_family.json, made by make_data.py from family_words.py) when they are here."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent

def load():
    d = json.loads((HERE / 'letters_data.json').read_text(encoding='utf-8'))
    f = HERE / 'letters_family.json'
    if f.exists():
        fam = json.loads(f.read_text(encoding='utf-8'))
        d['words'] = {**d['words'], **fam['words']}
        i = next((k for k, c in enumerate(d['clips']) if c['kind'] == 'prompt'), len(d['clips']))
        d['clips'] = d['clips'][:i] + fam['clips'] + d['clips'][i:]     # with the other words, before the sayings
        d['family'] = fam
    return d
