"""Wrap the page (app.html, written for the Claude preview) into a standalone index.html for hosting, and build the
Letters lock (_worker.js) with the key from learn_key.txt."""
import secrets
from pathlib import Path
site = Path(__file__).resolve().parent.parent / 'site'
body = (site / 'app.html').read_text(encoding='utf-8')
# the hosted site is for everyone: the plain link says "My Learning Lab"; gift links add ?for=Name
assert "const DEFAULT_OWNER = 'Sam';" in body
body = body.replace("const DEFAULT_OWNER = 'Sam';", "const DEFAULT_OWNER = '';", 1)
# Letters only for devices with the pass (see tools/_worker_src.js)
assert "const LETTERS_GATED = false;" in body
body = body.replace("const LETTERS_GATED = false;", "const LETTERS_GATED = true;", 1)
body = body.replace("<title>Sam's Learning Lab</title>", "<title>My Learning Lab</title>", 1)
body = body.replace('aria-label="Sam\'s Learning Lab"', 'aria-label="My Learning Lab"', 1)
SITE_URL = 'https://learn.mikeohalloran.au'
head_end = body.index('<style>')
head, rest = body[:head_end], body[head_end:]
style_end = rest.index('</style>') + len('</style>')
style, content = rest[:style_end], rest[style_end:]
page = f"""<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#FFF8EC">
<meta name="robots" content="noindex">
<link rel="icon" href="faces/F04.webp" type="image/webp">
<meta property="og:title" content="My Learning Lab">
<meta property="og:description" content="Letters and numbers games with the monsters.">
<meta property="og:image" content="{SITE_URL}/faces/F04.webp">
<meta property="og:url" content="{SITE_URL}/">
{head.strip()}
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}} body{{margin:0}} img{{max-width:100%}}</style>
{style}
</head>
<body>
{content.strip()}
</body>
</html>
"""
(site / 'index.html').write_text(page, encoding='utf-8')
print('wrote', site / 'index.html', len(page), 'bytes')

# the gatekeeper Cloudflare runs in front of the site, with the secret key from learn_key.txt (never in the repo)
keyfile = site.parent / 'learn_key.txt'
if not keyfile.exists(): keyfile.write_text(secrets.token_urlsafe(18) + '\n')
key = keyfile.read_text().strip()
assert len(key) >= 20 and key.replace('-', '').replace('_', '').isalnum()
worker = (Path(__file__).resolve().parent / '_worker_src.js').read_text(encoding='utf-8')
assert worker.count('__LETTERS_KEY__') == 1
(site / '_worker.js').write_text(worker.replace('__LETTERS_KEY__', key), encoding='utf-8')
print('wrote', site / '_worker.js')
