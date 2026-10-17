"""Everything the maths games' narrator says, in one list. Writes number_lines.json, which the voice maker
(number_voices.py, on the laptop) and the page both use.

    python3 lines.py"""
import json
from pathlib import Path

VOICE = 'en-au-tutor-3'          # Google's "Tutor 3": an Australian teacher's voice, made for teaching
BACKUP = 'en-au-storyteller-4'   # "Storyteller 4", warm and engaging, if Tutor 3 doesn't suit

WORDS = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
         'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty']
LINES = [{'id': f'n_{i}', 'kind': 'number', 'text': w} for i, w in enumerate(WORDS, 1)]
LINES += [
    # Monster count
    {'id': 'c_start', 'kind': 'prompt', 'text': "Let's count the monsters! Tap each one."},
    {'id': 'c_how_many', 'kind': 'prompt', 'text': 'How many monsters?'},
    {'id': 'c_already', 'kind': 'prompt', 'text': 'We counted that one!'},
    # Quick look
    {'id': 'q_look', 'kind': 'prompt', 'text': 'Quick look!'},
    {'id': 'q_how_many', 'kind': 'prompt', 'text': 'How many did you see?'},
    {'id': 'q_again', 'kind': 'prompt', 'text': 'Have another look.'},
    # all the games
    {'id': 'try_again', 'kind': 'prompt', 'text': 'Try again.'},
    {'id': 'p_yes', 'kind': 'praise', 'text': 'Yes!'},
    {'id': 'p_right', 'kind': 'praise', 'text': "That's right!"},
    {'id': 'p_great_counting', 'kind': 'praise', 'text': 'Great counting!'},
    {'id': 'p_sharp', 'kind': 'praise', 'text': 'Super sharp eyes!'},
    {'id': 'p_well_done', 'kind': 'praise', 'text': 'Well done!'},
]
STYLE = {
    'number': 'Say only this number, clearly and cheerfully, like counting along with a young child.',
    'prompt': 'Warm, playful and kind, speaking to a young child.',
    'praise': 'Delighted and proud, cheering on a young child.',
}

if __name__ == '__main__':
    assert len({l['id'] for l in LINES}) == len(LINES)
    out = {'voice': VOICE, 'backup': BACKUP, 'style': STYLE, 'lines': LINES}
    p = Path(__file__).resolve().parent / 'number_lines.json'
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'wrote {p.name}: {len(LINES)} lines')
