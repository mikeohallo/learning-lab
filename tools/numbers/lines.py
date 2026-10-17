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
    # Feed the monster
    *[{'id': f'f_want_{i}', 'kind': 'prompt', 'text': f"This monster wants {w} {'cookie' if i == 1 else 'cookies'}."} for i, w in enumerate(WORDS[:10], 1)],
    {'id': 'f_tap', 'kind': 'prompt', 'text': 'Tap the jar to put cookies on the plate.'},
    {'id': 'f_more', 'kind': 'prompt', 'text': 'Still hungry! Put some more on.'},
    {'id': 'f_less', 'kind': 'prompt', 'text': 'Oh no, too many! Take some away.'},
    {'id': 'f_one_more', 'kind': 'prompt', 'text': 'This monster wants one more!'},
    {'id': 'f_one_less', 'kind': 'prompt', 'text': 'This monster wants one less.'},
    {'id': 'f_yum', 'kind': 'praise', 'text': 'Yum yum!'},
    # More or less
    {'id': 'm_more', 'kind': 'prompt', 'text': 'Which side has more?'},
    {'id': 'm_fewer', 'kind': 'prompt', 'text': 'Which side has fewer?'},
    {'id': 'm_count', 'kind': 'prompt', 'text': "Let's count them."},
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
