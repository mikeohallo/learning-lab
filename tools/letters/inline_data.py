"""Paste the tracing paths and everyone's word list into the site's page (site/app.html), between the
/*LETTERS:paths*/ ... /*END*/ and /*LETTERS:data*/ ... /*END*/ markers, and put the family words (if any) in
site/letters/family.json, behind the Letters lock, where only family browsers (set up with the
private access link) load them from."""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
APP = HERE.parent / 'site' / 'app.html'
paths = json.loads((HERE / 'letters.json').read_text())['letters']
data = json.loads((HERE / 'letters_data.json').read_text(encoding='utf-8'))
P = {ch: {'advance': v['advance'], 'strokes': v['strokes']} for ch, v in paths.items()}
D = {'letters': {ch: {'word': v['word']} for ch, v in data['letters'].items()},
     'words': data['words'], 'spell': data['spell'], 'prompts': data['prompts']}
s = APP.read_text(encoding='utf-8')
for key, val in (('paths', P), ('data', D)):
    js = json.dumps(val, separators=(',', ':'), ensure_ascii=False)
    s, n = re.subn(r'/\*LETTERS:%s\*/.*?/\*END\*/' % key, lambda m: f'/*LETTERS:{key}*/{js}/*END*/', s, flags=re.S)
    assert n == 1, key
APP.write_text(s, encoding='utf-8')
print('inlined', len(json.dumps(P)) // 1024, 'KB of paths and', len(json.dumps(D)) // 1024, 'KB of words')
fam_in, fam_out = HERE / 'letters_family.json', APP.parent / 'letters' / 'family.json'
if fam_in.exists():
    fam = json.loads(fam_in.read_text(encoding='utf-8')); fam.pop('clips', None)
    fam_out.parent.mkdir(parents=True, exist_ok=True)
    fam_out.write_text(json.dumps(fam, separators=(',', ':'), ensure_ascii=False), encoding='utf-8'); print('wrote', fam_out)
elif fam_out.exists():
    fam_out.unlink(); print('no family words: removed', fam_out)
