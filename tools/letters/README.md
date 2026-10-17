# Letters game tools

The tools behind the Letters game (Trace, Spell, Sounds and First sound). They run in the working copy, where this folder sits next to `site/` (the page and its images), so paths like `../site/app.html` point there.

| File | What it does |
|---|---|
| `glyphs.py` | Loads the Edu NSW ACT Foundation font (`fonts/`, Open Font Licence) and rasterises letters |
| `strokes.py` | Traces each lowercase letter's centre line from the font, with the start point, direction and stroke order NSW Foundation Style teaches, and writes `letters.json` |
| `check.py`, `sheet.py` | Draw the paths with start dots, arrows and stroke numbers, to check against a school handwriting chart |
| `make_data.py` | The word list, letter sounds and names, sayings and pictures, written to `letters_data.json`. Family words for one child's own devices come from a private `family_words.py` (not in the repo) and go to a separate file that the game loads from behind the lock |
| `wordlist.py` | Gives the other tools the full list: everyone's words plus the family words when they're there |
| `inline_data.py` | Pastes `letters.json` and the word list into the page |
| `recorder_src.html`, `build_recorder.py` | A recording page that runs from a file in Chrome: one clip at a time, saved straight into a folder, with auto-stop on silence |
| `make_voices.py` | Turns recordings into the game's clips. For letter sounds it keeps the strongest take, because a short "p" or "h" often comes with a retry or a breath. Then trimming, level, fades, and a mono MP3 |
| `letters_gen_src.py`, `build_gen.py` | Draws the word pictures (hat, kite, sun…) with Google AI Studio's image model, in the book's style |
| `make_pictures.py` | Cuts the pictures out of their white background and makes 360 px WebP files |
| `voices_gen_src.py`, `build_voices_gen.py` | Text-to-speech with Gemini, kept for adding lines later. It does words and sayings well, but not isolated letter sounds (see the main README). `tests/` has a fake API for testing it offline |

The pictures, the family portraits and the recorded voices aren't in the repo.
