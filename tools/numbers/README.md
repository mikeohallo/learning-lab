# Numbers game tools

The narrator for the maths games (Monster count, Quick look and the ones after them). Like the Letters tools, they run in the working copy, where `site/` (the page) sits next to `numbers/`.

| File | What it does |
|---|---|
| `lines.py` | Every line the narrator says, the voice and the speaking style; writes `number_lines.json` |
| `number_voices.py`, `Make number voices.bat` | Makes the clips with Gemini text-to-speech in Google's Australian "Tutor 3" voice, paced for the free tier (10 a minute), then writes a listening page. Re-running only makes what's missing; `redo` remakes single lines and keeps the old takes; `--voice` switches voice. The API key is read from `GEMINI_API_KEY` |
| `make_number_voices.py` | Trims, levels and turns the clips into the site's MP3s and `index.json` |
| `inline_lines.py` | Puts the lines into the page, so it can show or say them before any clips exist |

The clips themselves aren't in the repo. Without them the games use the browser's own voice, or show the words. `tools/test_numbers.py` tests the voice maker against a fake API (`tools/letters/tests/mock_gemini.py`).
