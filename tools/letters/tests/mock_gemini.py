import base64, io, json, math, struct, sys, wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
MODE = sys.argv[2] if len(sys.argv) > 2 else 'normal'
state = {'tts': 0, 'design': 0, 'busy_done': False}
def tone(secs, pcm=False):
    n = int(24000 * secs); frames = b''.join(struct.pack('<h', int(8000 * math.sin(i / 10))) for i in range(n))
    if pcm: return frames
    b = io.BytesIO()
    with wave.open(b, 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(frames)
    return b.getvalue()
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        assert self.headers['x-goog-api-key'] == 'test-key'
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == '/v1beta/voices':
            if MODE == 'nolib': return self.send(200, {})
            v = [{'id': 'au-f-1', 'displayName': 'Matilda', 'description': 'Warm, Australian', 'gender': 'FEMALE', 'languageCode': 'en-AU'}]
            if 'accent' in q: v.append({'name': 'voices/au-m-1', 'displayName': 'Bruce', 'description': 'Easy-going Aussie', 'gender': 'MALE'})
            return self.send(200, {'voices': v})
        self.send(404, {'error': 'nope'})
    def do_POST(self):
        assert self.headers['x-goog-api-key'] == 'test-key'
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/v1beta/voices':
            state['design'] += 1
            if 'language_code' in body['voice'] and state['design'] == 1:
                return self.send(400, {'error': {'message': 'Unsupported language_code en-AU'}})
            assert body['voice']['type'] == 'prompted' and 'Australian' in body['voice']['prompted']['input']
            return self.send(200, {'id': f'voice_d{state["design"]}', 'sampleAudio': {'mimeType': 'audio/wav', 'data': base64.b64encode(tone(.3)).decode()}})
        if self.path == '/v1beta/interactions':
            state['tts'] += 1
            c = body['input'][0]['content'][0]
            if MODE == 'nostyle' and 'annotations' in c:
                return self.send(400, {'error': {'message': 'Invalid JSON payload received. Unknown name "annotations"'}})
            if MODE == 'busy' and not state['busy_done']:
                state['busy_done'] = True; return self.send(503, {'error': {'message': 'overloaded'}})
            if MODE == 'denied': return self.send(403, {'error': {'message': 'API key not valid'}})
            vid = body['generation_config']['speech_config'][0]['voice']
            secs = 0.25 + 0.05 * len(c['text'])
            if state['tts'] % 5 == 0:   # some raw PCM, SDK-like shape
                return self.send(200, {'output_audio': {'mime_type': 'audio/l16;rate=24000', 'data': base64.b64encode(tone(secs, True)).decode()}})
            return self.send(200, {'id': 'int_1', 'steps': [{'type': 'user_input'}, {'type': 'model_output', 'content': [{'type': 'audio', 'mimeType': 'audio/wav', 'data': base64.b64encode(tone(secs)).decode()}]}]})
        self.send(404, {'error': 'nope'})
HTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()
