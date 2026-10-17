"""The Letters game's word list, sounds, prompts and pictures, in one place.
Writes letters_data.json (everyone's words), which the recorder, the picture runner and the game all read.
Family words (Sam's devices only) come from family_words.py, which is private and not in the repo; when it is
there, they go to letters_family.json, which the game loads from behind the Letters lock."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent

# letter: (sound tip for the recorder, letter name as said in Australia, tracing word)
LETTERS = {
 'a': ('"a" as in bat. Short, not "ay".', 'ay', 'axolotl'),
 'b': ('Quick "b", lips pop. No "buh".', 'bee', 'bat'),
 'c': ('"k", as in cat.', 'see', 'cupcake'),
 'd': ('Quick "d", tongue tap. No "duh".', 'dee', 'dragon'),
 'e': ('"e" as in bed.', 'ee', 'egg'),
 'f': ('"fff", keep blowing.', 'ef', 'fox'),
 'g': ('"g" as in goat, quick. No "guh".', 'jee', 'goat'),
 'h': ('Just a breath, "h", as in hat.', 'aitch', 'hat'),
 'i': ('"i" as in igloo.', 'eye', 'igloo'),
 'j': ('"j" as in jellyfish, quick.', 'jay', 'jellyfish'),
 'k': ('"k", the same sound as c.', 'kay', 'kite'),
 'l': ('"lll", tongue up, hold it.', 'el', 'log'),
 'm': ('"mmm", lips closed.', 'em', 'mermaid'),
 'n': ('"nnn".', 'en', 'net'),
 'o': ('"o" as in octopus.', 'oh', 'octopus'),
 'p': ('"p", a puff of air. No "puh".', 'pee', 'penguin'),
 'q': ('"kw", as in queen.', 'cue', 'queen'),
 'r': ('"rrr", a little growl. No "ruh".', 'ar', 'rug'),
 's': ('"sss", like a snake.', 'ess', 'snail'),
 't': ('"t", a tongue tap. No "tuh".', 'tee', 'tent'),
 'u': ('"u" as in up.', 'you', 'umbrella'),
 'v': ('"vvv", buzzy lips.', 'vee', 'van'),
 'w': ('"w" as in web, short.', 'double-you', 'web'),
 'x': ('"ks", like the end of box.', 'ex', 'box'),
 'y': ('"y" as in yeti, short.', 'why', 'yeti'),
 'z': ('"zzz", like a bee.', 'zed', 'zip'),
}

# word: (how it's written on screen, picture). face:NN is a monster face; new:x a picture from the AI Studio runner.
WORDS = {
 'axolotl': ('axolotl', 'face:19'), 'bat': ('bat', 'face:14'), 'cupcake': ('cupcake', 'face:25'),
 'dragon': ('dragon', 'face:24'), 'egg': ('egg', 'new:egg'),
 'fox': ('fox', 'face:18'), 'goat': ('goat', 'new:goat'), 'hat': ('hat', 'new:hat'),
 'igloo': ('igloo', 'new:igloo'), 'jellyfish': ('jellyfish', 'face:27'), 'kite': ('kite', 'new:kite'), 'log': ('log', 'new:log'),
 'mermaid': ('mermaid', 'face:07'), 'net': ('net', 'new:net'), 'octopus': ('octopus', 'face:05'),
 'penguin': ('penguin', 'face:04'), 'queen': ('queen', 'new:queen'), 'rug': ('rug', 'new:rug'),
 'snail': ('snail', 'face:29'), 'tent': ('tent', 'new:tent'), 'umbrella': ('umbrella', 'new:umbrella'),
 'van': ('van', 'new:van'), 'web': ('web', 'new:web'), 'box': ('box', 'new:box'), 'yeti': ('yeti', 'face:09'), 'zip': ('zip', 'new:zip'),
 'sun': ('sun', 'new:sun'), 'pig': ('pig', 'new:pig'), 'cup': ('cup', 'new:cup'), 'bus': ('bus', 'new:bus'), 'bed': ('bed', 'new:bed'),
 'cat': ('cat', 'new:cat'), 'dog': ('dog', 'new:dog'), 'bug': ('bug', 'new:bug'), 'hen': ('hen', 'new:hen'),
 'frog': ('frog', 'face:10'), 'crab': ('crab', 'new:crab'), 'drum': ('drum', 'new:drum'), 'flag': ('flag', 'new:flag'), 'nest': ('nest', 'new:nest'),
}

# spelling levels: 1 = three sounds, 2 = four sounds, 3 = spell it from a bigger set of tiles (levels 1 and 2 mixed)
SPELL = {
 '1': ['fox', 'bat', 'sun', 'pig', 'cup', 'net', 'rug', 'van', 'web', 'box', 'zip', 'hat', 'log', 'bus', 'bed', 'cat', 'dog', 'bug', 'hen'],
 '2': ['frog', 'crab', 'drum', 'flag', 'nest', 'tent'],
}

PROMPTS = {
 'watch': 'Watch me first.', 'trace': 'Your turn. Trace the letter.', 'start': 'Start at the green dot.',
 'arrow': 'Follow the arrow.', 'line': 'Back to the line.', 'spell': "Let's spell it.", 'tap': 'Tap the letters to spell it.',
 'name': "Let's spell your name.", 'another': "Let's do another one.",
 'well_done': 'Well done!', 'did_it': 'You did it!', 'great_writing': 'Great writing!', 'great_spelling': 'Amazing spelling!',
 'sound_out': 'Sound it out with me.', 'listen': 'Listen.',
 'which': 'Which letter makes this sound?', 'starts': 'What does it start with?',
}
OPTIONAL = {'which', 'starts'}   # nice to have recorded; until they are, the game shows the words instead

# what each new picture should show (for the AI Studio runner)
NEW_PICTURES = {
 'hat': 'a red sun hat', 'igloo': 'a small white igloo made of snow blocks', 'kite': 'a diamond-shaped kite with a bow tail',
 'log': 'a short brown log', 'net': 'a butterfly net with a wooden handle', 'queen': 'a smiling queen with a gold crown and a purple dress',
 'rug': 'a striped round rug', 'tent': 'a small triangle camping tent', 'van': 'a little blue van, side view',
 'web': 'a round spider web', 'box': 'a cardboard box with the flaps open', 'zip': 'a big zip, half open, on a strip of fabric',
 'sun': 'a smiling yellow sun', 'pig': 'a pink pig standing side-on', 'cup': 'a cup with a handle',
 'bus': 'a yellow bus, side view', 'bed': 'a single bed with a pillow and blanket', 'cat': 'a sitting ginger cat',
 'dog': 'a sitting brown dog', 'bug': 'a red ladybug, top view', 'hen': 'a brown hen standing side-on',
 'crab': 'a red crab with two big claws', 'drum': 'a toy drum with two drumsticks', 'flag': 'a triangle pennant flag with bright rainbow stripes on a wooden stick (not any country\'s flag)',
 'nest': 'a bird nest with three blue eggs', 'egg': 'one white egg', 'goat': 'a white goat standing side-on',
 'umbrella': 'an open red umbrella',
}

def clips(words, letters=True, prompts=True):
    """Every clip each voice records, in recording order: id, what to say, tip."""
    out = []
    if letters:
        for ch, (tip, name, _w) in LETTERS.items():
            out.append({'id': f'sound_{ch}', 'say': ch, 'kind': 'sound', 'tip': tip})
        for ch, (tip, name, _w) in LETTERS.items():
            out.append({'id': f'name_{ch}', 'say': ch.upper(), 'kind': 'name', 'tip': f'The letter name: "{name}".'})
    for w, (text, pic) in words.items():
        out.append({'id': f'word_{w}', 'say': text, 'kind': 'word', 'tip': 'Say the word clearly, like reading it to her.'})
    if prompts:
        for k, text in PROMPTS.items():
            out.append({'id': f'say_{k}', 'say': text, 'kind': 'prompt', 'tip': 'Warm and clear.', **({'optional': True} if k in OPTIONAL else {})})
    return out

def load_family():
    try:
        import family_words as F
    except ImportError:
        return None
    return F

if __name__ == '__main__':
    missing = [v[2] for v in LETTERS.values() if v[2] not in WORDS] + [w for lv in SPELL.values() for w in lv if w not in WORDS]
    new_missing = [w for w, (t, p) in WORDS.items() if p.startswith('new:') and p[4:] not in NEW_PICTURES]
    assert not missing and not new_missing, (missing, new_missing)
    assert not any(p.startswith('family:') for t, p in WORDS.values()), 'family words belong in family_words.py'
    data = {'letters': {ch: {'tip': t, 'name': n, 'word': w} for ch, (t, n, w) in LETTERS.items()},
            'words': {w: {'text': t, 'pic': p} for w, (t, p) in WORDS.items()}, 'spell': SPELL, 'prompts': PROMPTS,
            'newPictures': NEW_PICTURES, 'clips': clips(WORDS)}
    (HERE / 'letters_data.json').write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')
    F = load_family(); fam_out = HERE / 'letters_family.json'
    if F:
        bad = [w for w in list(F.LETTERS.values()) + [x for lv in F.SPELL.values() for x in lv] if w not in F.WORDS]
        assert not bad, bad
        fam = {'letters': F.LETTERS, 'words': {w: {'text': t, 'pic': p} for w, (t, p) in F.WORDS.items()}, 'spell': F.SPELL,
               'clips': clips(F.WORDS, letters=False, prompts=False)}
        fam_out.write_text(json.dumps(fam, indent=1, ensure_ascii=False), encoding='utf-8')
    elif fam_out.exists():
        fam_out.unlink()
    n = len(data['clips']) + (len(F.WORDS) if F else 0)
    print(n, 'clips per voice', f'({len(F.WORDS)} of them family words)' if F else '(no family words)', ';',
          len(NEW_PICTURES), 'new pictures;', len(WORDS), 'words')
