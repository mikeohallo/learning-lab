"""Run voices_gen.py against mock_gemini.py, with waits skipped. From a scratch copy of the letters tools:
    python3 mock_gemini.py 8765 normal &        (modes: normal, nolib, nostyle, busy, denied)
    GEN_API_BASE=http://127.0.0.1:8765/v1beta GEMINI_API_KEY=test-key python3 run_with_mock.py samples
"""
import runpy, sys, time
time.sleep = lambda s: None
sys.argv = ['voices_gen.py'] + sys.argv[1:]
runpy.run_path('voices_gen.py', run_name='__main__')
